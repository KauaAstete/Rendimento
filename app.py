import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import os
import json
import re
from typing import Dict, Tuple, Optional
import time
import warnings
import numpy as np

# Suprimir warnings
warnings.filterwarnings('ignore')

# Configurar pandas para evitar problemas com numpy.bool
pd.set_option('future.no_silent_downcasting', True)

# ======================== CONFIGURAÇÕES ========================
ARQUIVO_USUARIOS = "usuarios.json"
PASTA_DADOS = "dados_usuarios"
VERSAO_SISTEMA = "2.0.1"

# Configurações da página
st.set_page_config(
    page_title="Sistema de Rendimentos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================== CLASSES E FUNÇÕES UTILITÁRIAS ========================
class GerenciadorUsuarios:
    @staticmethod
    def hash_senha(senha: str) -> str:
        """Cria hash seguro da senha"""
        return hashlib.sha256(senha.encode()).hexdigest()
    
    @staticmethod
    def validar_nome_usuario(nome: str) -> Tuple[bool, str]:
        """Valida nome de usuário"""
        if len(nome) < 3:
            return False, "Nome deve ter pelo menos 3 caracteres"
        if len(nome) > 20:
            return False, "Nome deve ter no máximo 20 caracteres"
        if not re.match("^[a-zA-Z0-9_]+$", nome):
            return False, "Use apenas letras, números e underscore"
        return True, "Válido"
    
    @staticmethod
    def validar_senha(senha: str) -> Tuple[bool, str]:
        """Valida força da senha"""
        if len(senha) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        if len(senha) > 50:
            return False, "Senha muito longa"
        if not re.search(r"[A-Za-z]", senha):
            return False, "Senha deve conter pelo menos uma letra"
        if not re.search(r"[0-9]", senha):
            return False, "Senha deve conter pelo menos um número"
        return True, "Senha forte"
    
    @staticmethod
    def carregar_usuarios() -> Dict:
        """Carrega usuários do arquivo"""
        try:
            with open(ARQUIVO_USUARIOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    @staticmethod
    def salvar_usuarios(usuarios: Dict) -> None:
        """Salva usuários no arquivo"""
        with open(ARQUIVO_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, ensure_ascii=False, indent=2)

class GerenciadorDados:
    @staticmethod
    def get_caminho_usuario(nome_usuario: str) -> str:
        """Retorna caminho da pasta do usuário"""
        return os.path.join(PASTA_DADOS, nome_usuario)
    
    @staticmethod
    def get_caminho_rendimentos(nome_usuario: str) -> str:
        """Retorna caminho do arquivo de rendimentos"""
        return os.path.join(PASTA_DADOS, nome_usuario, "rendimentos.csv")
    
    @staticmethod
    def carregar_dados(nome_usuario: str) -> pd.DataFrame:
        """Carrega dados do usuário"""
        try:
            caminho = GerenciadorDados.get_caminho_rendimentos(nome_usuario)
            if os.path.exists(caminho):
                df = pd.read_csv(caminho)
                if not df.empty:
                    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
                    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
                    df = df.dropna(subset=['Data', 'Valor'])
                    return df
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
        
        return pd.DataFrame(columns=['Data', 'Valor', 'Categoria', 'Descrição'])
    
    @staticmethod
    def salvar_dados(nome_usuario: str, df: pd.DataFrame) -> bool:
        """Salva dados do usuário"""
        try:
            caminho = GerenciadorDados.get_caminho_rendimentos(nome_usuario)
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            
            # Validar e limpar dados
            if df.empty:
                df = pd.DataFrame(columns=['Data', 'Valor', 'Categoria', 'Descrição'])
            else:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
                df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
                df = df.dropna(subset=['Data', 'Valor'])
            
            df.to_csv(caminho, index=False)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")
            return False
    
    @staticmethod
    def backup_dados(nome_usuario: str) -> bool:
        """Cria backup dos dados"""
        try:
            caminho_original = GerenciadorDados.get_caminho_rendimentos(nome_usuario)
            if os.path.exists(caminho_original):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                caminho_backup = caminho_original.replace('.csv', f'_backup_{timestamp}.csv')
                
                df = pd.read_csv(caminho_original)
                df.to_csv(caminho_backup, index=False)
                return True
        except:
            pass
        return False

class AnalisadorDados:
    @staticmethod
    def validar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Valida e limpa o DataFrame"""
        if df.empty:
            return pd.DataFrame(columns=['Data', 'Valor', 'Categoria', 'Descrição'])
        
        try:
            # Garantir que as colunas existem
            colunas_necessarias = ['Data', 'Valor', 'Categoria', 'Descrição']
            for col in colunas_necessarias:
                if col not in df.columns:
                    df[col] = ''
            
            # Converter tipos de dados
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            
            # Remover linhas com dados inválidos
            df = df.dropna(subset=['Data', 'Valor'])
            
            # Garantir que não há valores negativos
            df = df[df['Valor'] >= 0]
            
            return df.reset_index(drop=True)
        except Exception as e:
            st.error(f"Erro ao validar dados: {e}")
            return pd.DataFrame(columns=['Data', 'Valor', 'Categoria', 'Descrição'])
    
    @staticmethod
    def calcular_estatisticas(df: pd.DataFrame) -> Dict:
        """Calcula estatísticas dos dados"""
        if df.empty or len(df) == 0:
            return {
                'total_registros': 0,
                'total_valor': 0.0,
                'media_diaria': 0.0,
                'maior_valor': 0.0,
                'menor_valor': 0.0,
                'primeiro_registro': None,
                'ultimo_registro': None
            }
        
        # Garantir que os valores são numéricos
        df_copy = df.copy()
        df_copy['Valor'] = pd.to_numeric(df_copy['Valor'], errors='coerce')
        df_copy = df_copy.dropna(subset=['Valor'])
        
        if df_copy.empty:
            return {
                'total_registros': 0,
                'total_valor': 0.0,
                'media_diaria': 0.0,
                'maior_valor': 0.0,
                'menor_valor': 0.0,
                'primeiro_registro': None,
                'ultimo_registro': None
            }
        
        return {
            'total_registros': len(df_copy),
            'total_valor': float(df_copy['Valor'].sum()),
            'media_diaria': float(df_copy['Valor'].mean()),
            'maior_valor': float(df_copy['Valor'].max()),
            'menor_valor': float(df_copy['Valor'].min()),
            'primeiro_registro': df_copy['Data'].min(),
            'ultimo_registro': df_copy['Data'].max()
        }
    
    @staticmethod
    def tendencia_mensal(df: pd.DataFrame) -> str:
        """Analisa tendência mensal"""
        if len(df) < 2:
            return "Dados insuficientes"
        
        df_mensal = df.groupby(df['Data'].dt.to_period('M'))['Valor'].sum()
        
        if len(df_mensal) < 2:
            return "Dados insuficientes"
        
        ultimos_dois = df_mensal.tail(2)
        if ultimos_dois.iloc[1] > ultimos_dois.iloc[0]:
            return "📈 Crescimento"
        elif ultimos_dois.iloc[1] < ultimos_dois.iloc[0]:
            return "📉 Declínio"
        else:
            return "➡️ Estável"

# ======================== INTERFACE ========================
def aplicar_tema_customizado():
    """Aplica tema customizado"""
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
        }
        .metric-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 0.75rem;
            border-radius: 5px;
            border: 1px solid #c3e6cb;
            margin: 1rem 0;
        }
        .warning-message {
            background: #fff3cd;
            color: #856404;
            padding: 0.75rem;
            border-radius: 5px;
            border: 1px solid #ffeaa7;
            margin: 1rem 0;
        }
        .sidebar .sidebar-content {
            background: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)

def sidebar_info():
    """Sidebar com informações do sistema"""
    with st.sidebar:
        st.markdown("### 📊 Sistema de Rendimentos")
        st.markdown(f"**Versão:** {VERSAO_SISTEMA}")
        
        if st.session_state.get('logado', False):
            st.markdown("---")
            st.markdown("### 👤 Usuário")
            st.markdown(f"**Nome:** {st.session_state.get('nome_completo', 'N/A')}")
            st.markdown(f"**Login:** {st.session_state.get('usuario_atual', 'N/A')}")
            
            # Estatísticas rápidas
            try:
                df_raw = GerenciadorDados.carregar_dados(st.session_state.usuario_atual)
                df = AnalisadorDados.validar_dataframe(df_raw)
                stats = AnalisadorDados.calcular_estatisticas(df)
                
                st.markdown("---")
                st.markdown("### 📈 Resumo Rápido")
                st.metric("Total de Registros", stats['total_registros'])
                st.metric("Total Acumulado", f"R$ {stats['total_valor']:,.2f}")
                
                if stats['total_registros'] > 0:
                    st.metric("Média por Registro", f"R$ {stats['media_diaria']:,.2f}")
                    st.markdown(f"**Tendência:** {AnalisadorDados.tendencia_mensal(df)}")
            except Exception as e:
                st.error(f"Erro ao carregar estatísticas: {e}")
            
            st.markdown("---")
            
            # Botões de ação
            if st.button("🔄 Atualizar Dados", use_container_width=True):
                st.rerun()
            
            if st.button("💾 Backup", use_container_width=True):
                if GerenciadorDados.backup_dados(st.session_state.usuario_atual):
                    st.success("Backup criado!")
                else:
                    st.error("Erro no backup")
            
            if st.button("🚪 Sair", use_container_width=True, type="secondary"):
                for key in ['logado', 'usuario_atual', 'nome_completo']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

def tela_login():
    """Tela de login melhorada"""
    aplicar_tema_customizado()
    
    # Cabeçalho
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Sistema de Controle de Rendimentos</h1>
        <p>Gerencie seus rendimentos de forma segura e organizada</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs melhoradas
    tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Cadastro", "ℹ️ Sobre"])
    
    with tab1:
        st.markdown("### Fazer Login")
        
        with st.form("form_login"):
            nome_usuario = st.text_input("👤 Nome de usuário", placeholder="Digite seu nome de usuário")
            senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            col1, col2 = st.columns(2)
            with col1:
                botao_login = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")
            with col2:
                lembrar = st.checkbox("Lembrar usuário")
            
            if botao_login:
                if nome_usuario and senha:
                    usuarios = GerenciadorUsuarios.carregar_usuarios()
                    
                    if nome_usuario in usuarios:
                        if usuarios[nome_usuario]['senha'] == GerenciadorUsuarios.hash_senha(senha):
                            st.session_state.logado = True
                            st.session_state.usuario_atual = nome_usuario
                            st.session_state.nome_completo = usuarios[nome_usuario]['nome_completo']
                            
                            # Atualizar último login
                            usuarios[nome_usuario]['ultimo_login'] = datetime.now().isoformat()
                            GerenciadorUsuarios.salvar_usuarios(usuarios)
                            
                            st.success("✅ Login realizado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Senha incorreta!")
                    else:
                        st.error("❌ Usuário não encontrado!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")
    
    with tab2:
        st.markdown("### Criar Nova Conta")
        
        with st.form("form_cadastro"):
            nome_usuario = st.text_input("👤 Nome de usuário", 
                                       placeholder="Ex: joao_silva",
                                       help="Apenas letras, números e underscore")
            nome_completo = st.text_input("📝 Nome completo", 
                                        placeholder="Ex: João da Silva")
            email = st.text_input("📧 Email (opcional)", 
                                placeholder="Ex: joao@email.com")
            senha = st.text_input("🔒 Senha", type="password", 
                                placeholder="Mínimo 6 caracteres com letra e número")
            confirmar_senha = st.text_input("🔒 Confirmar senha", type="password")
            
            aceitar_termos = st.checkbox("Aceito os termos de uso")
            
            botao_cadastro = st.form_submit_button("✨ Criar Conta", 
                                                 use_container_width=True, 
                                                 type="primary")
            
            if botao_cadastro:
                # Validações
                if not all([nome_usuario, nome_completo, senha, confirmar_senha]):
                    st.error("❌ Preencha todos os campos obrigatórios!")
                elif not aceitar_termos:
                    st.error("❌ Aceite os termos de uso!")
                else:
                    # Validar nome de usuário
                    valido, msg = GerenciadorUsuarios.validar_nome_usuario(nome_usuario)
                    if not valido:
                        st.error(f"❌ Nome de usuário: {msg}")
                    else:
                        # Validar senha
                        valido, msg = GerenciadorUsuarios.validar_senha(senha)
                        if not valido:
                            st.error(f"❌ Senha: {msg}")
                        elif senha != confirmar_senha:
                            st.error("❌ Senhas não coincidem!")
                        else:
                            # Verificar se usuário existe
                            usuarios = GerenciadorUsuarios.carregar_usuarios()
                            if nome_usuario in usuarios:
                                st.error("❌ Usuário já existe!")
                            else:
                                # Criar usuário
                                usuarios[nome_usuario] = {
                                    'senha': GerenciadorUsuarios.hash_senha(senha),
                                    'nome_completo': nome_completo,
                                    'email': email,
                                    'data_criacao': datetime.now().isoformat(),
                                    'ultimo_login': None
                                }
                                
                                GerenciadorUsuarios.salvar_usuarios(usuarios)
                                os.makedirs(GerenciadorDados.get_caminho_usuario(nome_usuario), exist_ok=True)
                                
                                st.success("✅ Conta criada com sucesso!")
                                st.balloons()
                                time.sleep(2)
                                st.rerun()
    
    with tab3:
        st.markdown("### Sobre o Sistema")
        st.markdown(f"""
        **Versão:** {VERSAO_SISTEMA}
        
        **Características:**
        - 🔒 Sistema de autenticação seguro
        - 👥 Suporte a múltiplos usuários
        - 📊 Análises e relatórios detalhados
        - 📈 Gráficos interativos
        - 💾 Backup automático dos dados
        - 🎨 Interface moderna e responsiva
        
        **Funcionalidades:**
        - Controle de rendimentos por categoria
        - Relatórios diários, semanais e mensais
        - Análise de tendências
        - Exportação de dados
        - Backup e restauração
        """)

def tela_principal():
    """Tela principal aprimorada"""
    aplicar_tema_customizado()
    sidebar_info()
    
    # Cabeçalho principal
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 Painel de Controle</h1>
        <p>Bem-vindo(a), <strong>{st.session_state.nome_completo}</strong>!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carregar e validar dados
    df_raw = GerenciadorDados.carregar_dados(st.session_state.usuario_atual)
    df = AnalisadorDados.validar_dataframe(df_raw)
    
    # Abas principais
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Adicionar", "📋 Gerenciar", "📊 Análises", "⚙️ Configurações"])
    
    with tab1:
        formulario_adicionar(df)
    
    with tab2:
        gerenciar_dados(df)
    
    with tab3:
        analises_avancadas(df)
    
    with tab4:
        configuracoes_usuario()

def formulario_adicionar(df):
    """Formulário aprimorado para adicionar rendimentos"""
    st.markdown("### ➕ Adicionar Novo Rendimento")
    
    with st.form("form_adicionar"):
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("📅 Data", value=datetime.today())
            valor = st.number_input("💰 Valor (R$)", min_value=0.01, format="%.2f", step=0.01)
        
        with col2:
            categorias = ["Salário", "Freelance", "Investimentos", "Vendas", "Aluguel", "Outros"]
            categoria = st.selectbox("🏷️ Categoria", categorias)
            descricao = st.text_input("📝 Descrição (opcional)", placeholder="Ex: Salário mensal")
        
        # Botão de envio
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            enviar = st.form_submit_button("✅ Adicionar Rendimento", 
                                         use_container_width=True, 
                                         type="primary")
        
        if enviar and valor > 0:
            novo_registro = pd.DataFrame({
                'Data': [data],
                'Valor': [valor],
                'Categoria': [categoria],
                'Descrição': [descricao or ""]
            })
            
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            
            if GerenciadorDados.salvar_dados(st.session_state.usuario_atual, df_atualizado):
                st.success("✅ Rendimento adicionado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Erro ao salvar dados!")

def gerenciar_dados(df):
    """Interface para gerenciar dados existentes"""
    st.markdown("### 📋 Gerenciar Rendimentos")
    
    if df.empty:
        st.info("🔍 Nenhum rendimento registrado ainda.")
        return
    
    # Filtros
    st.markdown("#### 🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'Categoria' in df.columns:
            categorias = ['Todas'] + sorted(df['Categoria'].unique().tolist())
            categoria_filtro = st.selectbox("Categoria", categorias)
        else:
            categoria_filtro = 'Todas'
    
    with col2:
        data_inicio = st.date_input("Data início", value=df['Data'].min())
    
    with col3:
        data_fim = st.date_input("Data fim", value=df['Data'].max())
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if categoria_filtro != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_filtro]
    
    df_filtrado = df_filtrado[
        (df_filtrado['Data'] >= pd.Timestamp(data_inicio)) & 
        (df_filtrado['Data'] <= pd.Timestamp(data_fim))
    ]
    
    # Editor de dados simplificado
    if not df_filtrado.empty:
        st.markdown("#### 📊 Dados Filtrados")
        
        # Mostrar dados em tabela não editável
        st.dataframe(
            df_filtrado.sort_values('Data', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Seleção de registros para exclusão
        st.markdown("#### 🗑️ Excluir Registros")
        
        # Criar lista de registros para seleção
        registros_opcoes = []
        for idx, row in df_filtrado.iterrows():
            opcao = f"{row['Data'].strftime('%d/%m/%Y')} - {row['Categoria']} - R$ {row['Valor']:,.2f}"
            if row['Descrição']:
                opcao += f" - {row['Descrição']}"
            registros_opcoes.append((idx, opcao))
        
        indices_selecionados = st.multiselect(
            "Selecione os registros para excluir:",
            options=[idx for idx, _ in registros_opcoes],
            format_func=lambda x: next(opcao for idx, opcao in registros_opcoes if idx == x)
        )
        
        # Botões de ação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Excluir Selecionados", 
                        use_container_width=True, 
                        disabled=len(indices_selecionados) == 0,
                        type="secondary"):
                
                # Remover registros selecionados
                df_atualizado = df.drop(indices_selecionados).reset_index(drop=True)
                
                if GerenciadorDados.salvar_dados(st.session_state.usuario_atual, df_atualizado):
                    st.success(f"✅ {len(indices_selecionados)} registro(s) excluído(s)!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao excluir registros!")
        
        with col2:
            if st.button("📊 Exportar Filtrados", use_container_width=True):
                csv = df_filtrado.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"rendimentos_filtrados_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("📈 Analisar Filtrados", use_container_width=True):
                st.markdown("#### 📊 Estatísticas dos Dados Filtrados")
                stats = AnalisadorDados.calcular_estatisticas(df_filtrado)
                
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.metric("Total de Registros", stats['total_registros'])
                    st.metric("Valor Total", f"R$ {stats['total_valor']:,.2f}")
                
                with col_stat2:
                    st.metric("Média", f"R$ {stats['media_diaria']:,.2f}")
                    st.metric("Maior Valor", f"R$ {stats['maior_valor']:,.2f}")

def analises_avancadas(df):
    """Análises e relatórios avançados"""
    st.markdown("### 📊 Análises Avançadas")
    
    if df.empty:
        st.info("🔍 Adicione alguns rendimentos para ver as análises.")
        return
    
    # Estatísticas gerais
    stats = AnalisadorDados.calcular_estatisticas(df)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", stats['total_registros'])
    
    with col2:
        st.metric("Total Acumulado", f"R$ {stats['total_valor']:,.2f}")
    
    with col3:
        st.metric("Média por Registro", f"R$ {stats['media_diaria']:,.2f}")
    
    with col4:
        st.metric("Maior Valor", f"R$ {stats['maior_valor']:,.2f}")
    
    # Gráficos
    st.markdown("#### 📈 Visualizações")
    
    try:
        # Gráfico de linha temporal
        df_temporal = df.groupby('Data')['Valor'].sum().reset_index()
        
        fig_temporal = px.line(
            df_temporal, 
            x='Data', 
            y='Valor',
            title='Evolução dos Rendimentos ao Longo do Tempo',
            labels={'Valor': 'Valor (R$)', 'Data': 'Data'}
        )
        fig_temporal.update_traces(mode='lines+markers')
        st.plotly_chart(fig_temporal, use_container_width=True)
        
        # Gráfico por categoria (se existir)
        if 'Categoria' in df.columns and not df['Categoria'].isna().all():
            col1, col2 = st.columns(2)
            
            with col1:
                df_categoria = df.groupby('Categoria')['Valor'].sum().reset_index()
                
                fig_categoria = px.pie(
                    df_categoria, 
                    values='Valor', 
                    names='Categoria',
                    title='Distribuição por Categoria'
                )
                st.plotly_chart(fig_categoria, use_container_width=True)
            
            with col2:
                fig_categoria_bar = px.bar(
                    df_categoria, 
                    x='Categoria', 
                    y='Valor',
                    title='Valores por Categoria'
                )
                st.plotly_chart(fig_categoria_bar, use_container_width=True
