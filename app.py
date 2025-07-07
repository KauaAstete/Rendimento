import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import hashlib
import os
import json

# Arquivos de dados
ARQUIVO_USUARIOS = "usuarios.json"
PASTA_DADOS = "dados_usuarios"

def hash_senha(senha):
    """Cria hash da senha para segurança"""
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_usuarios():
    """Carrega lista de usuários do arquivo JSON"""
    try:
        with open(ARQUIVO_USUARIOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def salvar_usuarios(usuarios):
    """Salva lista de usuários no arquivo JSON"""
    with open(ARQUIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

def criar_usuario(nome_usuario, senha, nome_completo):
    """Cria novo usuário"""
    usuarios = carregar_usuarios()
    
    if nome_usuario in usuarios:
        return False, "Usuário já existe!"
    
    usuarios[nome_usuario] = {
        "senha": hash_senha(senha),
        "nome_completo": nome_completo,
        "data_criacao": datetime.now().isoformat()
    }
    
    salvar_usuarios(usuarios)
    
    # Criar pasta para dados do usuário
    pasta_usuario = os.path.join(PASTA_DADOS, nome_usuario)
    os.makedirs(pasta_usuario, exist_ok=True)
    
    return True, "Usuário criado com sucesso!"

def verificar_login(nome_usuario, senha):
    """Verifica se login está correto"""
    usuarios = carregar_usuarios()
    
    if nome_usuario not in usuarios:
        return False, "Usuário não encontrado!"
    
    if usuarios[nome_usuario]["senha"] != hash_senha(senha):
        return False, "Senha incorreta!"
    
    return True, "Login realizado com sucesso!"

def get_caminho_dados_usuario(nome_usuario):
    """Retorna caminho do arquivo de dados do usuário"""
    pasta_usuario = os.path.join(PASTA_DADOS, nome_usuario)
    return os.path.join(pasta_usuario, "rendimentos.csv")

def carregar_dados_usuario(nome_usuario):
    """Carrega dados específicos do usuário"""
    try:
        caminho_arquivo = get_caminho_dados_usuario(nome_usuario)
        df = pd.read_csv(caminho_arquivo, parse_dates=["Data"])
        if "Data" not in df.columns or "Valor" not in df.columns:
            return pd.DataFrame(columns=["Data", "Valor"])
        return df
    except Exception:
        return pd.DataFrame(columns=["Data", "Valor"])

def salvar_dados_usuario(nome_usuario, df):
    """Salva dados específicos do usuário"""
    if not df.empty and {"Data", "Valor"}.issubset(df.columns):
        # Garantir que as datas são válidas antes de salvar
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        
        if not df.empty:
            caminho_arquivo = get_caminho_dados_usuario(nome_usuario)
            os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
            df.to_csv(caminho_arquivo, index=False)
            return True
        else:
            st.warning("⚠️ Nenhum dado válido para salvar.")
            return False
    else:
        st.warning("⚠️ Dados inválidos ou vazios — nada foi salvo.")
        return False

def tela_login():
    """Tela de login e cadastro"""
    st.title("🔐 Sistema de Controle de Rendimentos")
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        st.subheader("Fazer Login")
        
        with st.form("form_login"):
            nome_usuario = st.text_input("Nome de usuário")
            senha = st.text_input("Senha", type="password")
            botao_login = st.form_submit_button("Entrar")
            
            if botao_login:
                if nome_usuario and senha:
                    sucesso, mensagem = verificar_login(nome_usuario, senha)
                    if sucesso:
                        st.session_state.logado = True
                        st.session_state.usuario_atual = nome_usuario
                        usuarios = carregar_usuarios()
                        st.session_state.nome_completo = usuarios[nome_usuario]["nome_completo"]
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)
                else:
                    st.warning("Por favor, preencha todos os campos!")
    
    with tab2:
        st.subheader("Criar Nova Conta")
        
        with st.form("form_cadastro"):
            nome_usuario_novo = st.text_input("Nome de usuário (sem espaços)")
            nome_completo = st.text_input("Nome completo")
            senha_nova = st.text_input("Senha", type="password")
            confirmar_senha = st.text_input("Confirmar senha", type="password")
            botao_cadastro = st.form_submit_button("Criar conta")
            
            if botao_cadastro:
                if nome_usuario_novo and nome_completo and senha_nova and confirmar_senha:
                    if " " in nome_usuario_novo:
                        st.error("Nome de usuário não pode conter espaços!")
                    elif len(senha_nova) < 4:
                        st.error("Senha deve ter pelo menos 4 caracteres!")
                    elif senha_nova != confirmar_senha:
                        st.error("Senhas não coincidem!")
                    else:
                        sucesso, mensagem = criar_usuario(nome_usuario_novo, senha_nova, nome_completo)
                        if sucesso:
                            st.success(mensagem)
                            st.balloons()
                        else:
                            st.error(mensagem)
                else:
                    st.warning("Por favor, preencha todos os campos!")

def tela_principal():
    """Tela principal do sistema"""
    # Cabeçalho com informações do usuário
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📊 Controle de Rendimentos")
        st.write(f"Bem-vindo(a), **{st.session_state.nome_completo}**!")
    
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.session_state.nome_completo = None
            st.rerun()

    # --- Formulário para adicionar novo rendimento ---
    with st.form("form_rendimento_adicionar"):
        st.subheader("➕ Adicionar Novo Rendimento")
        
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data do rendimento", value=datetime.today())
        with col2:
            valor = st.number_input("Valor do rendimento (R$)", format="%.2f")
        
        enviado = st.form_submit_button("Adicionar rendimento")

        if enviado and valor != 0:
            # Recarregar dados do arquivo para garantir consistência
            df_atual = carregar_dados_usuario(st.session_state.usuario_atual)
            novo_dado = pd.DataFrame({"Data": [data], "Valor": [valor]})
            df_atualizado = pd.concat([df_atual, novo_dado], ignore_index=True)
            
            if salvar_dados_usuario(st.session_state.usuario_atual, df_atualizado):
                st.success("✅ Rendimento adicionado com sucesso!")
                st.rerun()

    # --- Carregamento dos dados ---
    df = carregar_dados_usuario(st.session_state.usuario_atual)

    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        df = df.sort_values("Data").reset_index(drop=True)

        st.subheader("📅 Gerenciar Rendimentos")

        # Criar uma cópia limpa para edição
        df_editavel = df.copy()
        df_editavel["Excluir"] = False

        # Usar uma chave única para o data_editor
        df_editado = st.data_editor(
            df_editavel,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            key="editor_rendimentos",
            column_config={
                "Data": st.column_config.DateColumn("Data"),
                "Valor": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
                "Excluir": st.column_config.CheckboxColumn("Excluir")
            }
        )

        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Salvar alterações", key="salvar_alteracoes"):
                # Filtrar dados não marcados para exclusão
                df_salvo = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
                
                # Validar e limpar dados
                df_salvo = df_salvo.copy()
                df_salvo["Data"] = pd.to_datetime(df_salvo["Data"], errors="coerce")
                df_salvo = df_salvo.dropna(subset=["Data"])
                
                if not df_salvo.empty:
                    if salvar_dados_usuario(st.session_state.usuario_atual, df_salvo):
                        st.success("✅ Alterações salvas com sucesso!")
                        st.rerun()
                else:
                    st.warning("⚠️ Nenhum dado válido para salvar.")

        with col2:
            if st.button("🗑️ Excluir selecionados", key="excluir_selecionados"):
                # Contar quantos itens serão excluídos
                itens_excluir = df_editado["Excluir"].sum()
                
                if itens_excluir > 0:
                    df_restante = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
                    
                    if not df_restante.empty:
                        if salvar_dados_usuario(st.session_state.usuario_atual, df_restante):
                            st.success(f"✅ {itens_excluir} registro(s) excluído(s) com sucesso!")
                            st.rerun()
                    else:
                        # Se não há dados restantes, criar arquivo vazio
                        df_vazio = pd.DataFrame(columns=["Data", "Valor"])
                        caminho_arquivo = get_caminho_dados_usuario(st.session_state.usuario_atual)
                        df_vazio.to_csv(caminho_arquivo, index=False)
                        st.success(f"✅ Todos os registros foram excluídos!")
                        st.rerun()
                else:
                    st.warning("⚠️ Nenhum item selecionado para exclusão.")

        with col3:
            # Mostrar estatísticas rápidas
            total_registros = len(df)
            total_valor = df["Valor"].sum()
            st.metric("📊 Total de Registros", total_registros)
            st.metric("💰 Total Acumulado", f"R$ {total_valor:.2f}")

        # --- Processar dados para resumos ---
        df_para_resumo = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
        
        if not df_para_resumo.empty:
            df_para_resumo["Data"] = pd.to_datetime(df_para_resumo["Data"], errors="coerce")
            df_para_resumo = df_para_resumo.dropna(subset=["Data"])
            
            df_para_resumo["Dia"] = df_para_resumo["Data"].dt.date
            df_para_resumo["Semana"] = df_para_resumo["Data"].dt.isocalendar().week
            df_para_resumo["Mês"] = df_para_resumo["Data"].dt.to_period("M").astype(str)

            # --- Resumo Diário com filtro por mês ---
            resumo_dia = df_para_resumo.groupby("Dia")["Valor"].sum().reset_index()
            resumo_dia.columns = ["Data", "Total (R$)"]
            resumo_dia["Mês"] = resumo_dia["Data"].astype(str).str.slice(0, 7)

            if not resumo_dia.empty:
                st.subheader("📈 Relatórios e Análises")
                
                meses_disponiveis = sorted(resumo_dia["Mês"].unique(), reverse=True)
                mes_selecionado = st.selectbox("Selecione o mês para ver o resumo diário", meses_disponiveis)

                resumo_dia_mes = resumo_dia[resumo_dia["Mês"] == mes_selecionado]

                st.subheader(f"📆 Resumo Diário de {mes_selecionado}")
                st.dataframe(resumo_dia_mes.drop(columns=["Mês"]).style.format({"Total (R$)": "R$ {:.2f}"}), use_container_width=True)

                fig_dia_mes = px.line(
                    resumo_dia_mes,
                    x="Data",
                    y="Total (R$)",
                    title=f"Rendimento Diário em {mes_selecionado}",
                    labels={"Data": "Data", "Total (R$)": "Total (R$)"}
                )
                fig_dia_mes.update_traces(mode="lines+markers")
                fig_dia_mes.update_layout(yaxis_title="Total (R$)", xaxis_title="Data", xaxis_tickformat="%d/%m/%Y")
                st.plotly_chart(fig_dia_mes, use_container_width=True)

            # --- Resumo Semanal ---
            st.subheader("🗓️ Resumo Semanal")
            resumo_semana = df_para_resumo.groupby("Semana")["Valor"].sum().reset_index()
            resumo_semana.columns = ["Semana", "Total (R$)"]
            st.dataframe(resumo_semana.style.format({"Total (R$)": "R$ {:.2f}"}))

            fig_semana = px.line(
                resumo_semana,
                x="Semana",
                y="Total (R$)",
                title="Rendimento Semanal",
                labels={"Semana": "Semana do Ano", "Total (R$)": "Total (R$)"}
            )
            fig_semana.update_traces(mode="markers+lines")
            st.plotly_chart(fig_semana, use_container_width=True)

            # --- Resumo Mensal ---
            st.subheader("📅 Resumo Mensal")
            resumo_mes = df_para_resumo.groupby("Mês")["Valor"].sum().reset_index()
            resumo_mes.columns = ["Mês", "Total (R$)"]
            st.dataframe(resumo_mes.style.format({"Total (R$)": "R$ {:.2f}"}))

            fig_mes = px.bar(
                resumo_mes,
                x="Mês",
                y="Total (R$)",
                title="Rendimento Mensal",
                labels={"Mês": "Mês", "Total (R$)": "Total (R$)"},
                text="Total (R$)"
            )
            fig_mes.update_traces(texttemplate="R$ %{text:.2f}", textposition="outside")
            fig_mes.update_layout(yaxis_title="Total (R$)", xaxis_title="Mês")
            st.plotly_chart(fig_mes, use_container_width=True)

    else:
        st.info("🔎 Nenhum rendimento registrado ainda. Comece adicionando seu primeiro rendimento!")

# --- MAIN ---
# Inicializar session state
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = None
if 'nome_completo' not in st.session_state:
    st.session_state.nome_completo = None

# Criar pasta de dados se não existir
os.makedirs(PASTA_DADOS, exist_ok=True)

# Roteamento da aplicação
if not st.session_state.logado:
    tela_login()
else:
    tela_principal()