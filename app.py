import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import json
import os

ARQUIVO_DADOS = "rendimentos.csv"
ARQUIVO_USUARIOS = "usuarios.json"
ARQUIVO_METAS = "metas.json"

# Funções de autenticação
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def carregar_usuarios():
    try:
        with open(ARQUIVO_USUARIOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)

def carregar_metas():
    try:
        with open(ARQUIVO_METAS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def salvar_metas(metas):
    with open(ARQUIVO_METAS, 'w', encoding='utf-8') as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)

def verificar_login(username, password):
    usuarios = carregar_usuarios()
    if username in usuarios:
        return usuarios[username]['password'] == hash_password(password)
    return False

def criar_usuario(username, password, nome_completo):
    usuarios = carregar_usuarios()
    if username not in usuarios:
        usuarios[username] = {
            'password': hash_password(password),
            'nome_completo': nome_completo,
            'data_criacao': datetime.now().isoformat()
        }
        salvar_usuarios(usuarios)
        return True
    return False

def carregar_dados():
    try:
        df = pd.read_csv(ARQUIVO_DADOS, parse_dates=["Data"])
        if "Data" not in df.columns or "Valor" not in df.columns:
            return pd.DataFrame(columns=["Data", "Valor", "Usuario"])
        
        # Verificar se a coluna Usuario existe, se não, criar com valor padrão
        if "Usuario" not in df.columns:
            df["Usuario"] = "usuario_antigo"  # Atribuir dados antigos a um usuário padrão
        
        return df
    except Exception:
        return pd.DataFrame(columns=["Data", "Valor", "Usuario"])

def salvar_dados(df):
    if not df.empty and {"Data", "Valor", "Usuario"}.issubset(df.columns):
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        
        if not df.empty:
            df.to_csv(ARQUIVO_DADOS, index=False)
            return True
        else:
            st.warning("⚠️ Nenhum dado válido para salvar.")
            return False
    else:
        st.warning("⚠️ Dados inválidos ou vazios — nada foi salvo.")
        return False

def obter_meta_diaria(usuario):
    metas = carregar_metas()
    return metas.get(usuario, {}).get('meta_diaria', 0.0)

def salvar_meta_diaria(usuario, meta):
    metas = carregar_metas()
    if usuario not in metas:
        metas[usuario] = {}
    metas[usuario]['meta_diaria'] = meta
    salvar_metas(metas)

def calcular_progresso_meta(df_usuario, data_atual, meta_diaria):
    if df_usuario.empty or meta_diaria == 0:
        return 0.0, 0.0, "🔴"
    
    # Rendimento do dia atual
    rendimento_hoje = df_usuario[df_usuario['Data'].dt.date == data_atual]['Valor'].sum()
    
    # Calcular progresso
    progresso = (rendimento_hoje / meta_diaria) * 100
    
    # Determinar emoji do status
    if progresso >= 100:
        status = "🟢"
    elif progresso >= 75:
        status = "🟡"
    elif progresso >= 50:
        status = "🟠"
    else:
        status = "🔴"
    
    return rendimento_hoje, progresso, status

# Inicializar session state
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = carregar_dados()
if 'lembrar_login' not in st.session_state:
    st.session_state.lembrar_login = False

# --- Sistema de Login ---
if st.session_state.usuario_logado is None:
    st.title("🔐 Sistema de Login")
    
    tab1, tab2 = st.tabs(["Login", "Criar Conta"])
    
    with tab1:
        st.subheader("Fazer Login")
        
        # Carregar dados salvos se existirem
        dados_salvos = {}
        if os.path.exists('.login_data.json'):
            try:
                with open('.login_data.json', 'r') as f:
                    dados_salvos = json.load(f)
            except:
                dados_salvos = {}
        
        username = st.text_input("Nome de usuário", value=dados_salvos.get('username', ''))
        password = st.text_input("Senha", type="password")
        lembrar = st.checkbox("Lembrar meus dados", value=dados_salvos.get('lembrar', False))
        
        if st.button("Entrar"):
            if verificar_login(username, password):
                st.session_state.usuario_logado = username
                st.session_state.lembrar_login = lembrar
                
                # Salvar dados de login se solicitado
                if lembrar:
                    dados_login = {
                        'username': username,
                        'lembrar': True
                    }
                    with open('.login_data.json', 'w') as f:
                        json.dump(dados_login, f)
                else:
                    # Remover dados salvos se não quiser lembrar
                    if os.path.exists('.login_data.json'):
                        os.remove('.login_data.json')
                
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos!")
    
    with tab2:
        st.subheader("Criar Nova Conta")
        novo_username = st.text_input("Nome de usuário", key="novo_user")
        novo_nome = st.text_input("Nome completo", key="novo_nome")
        nova_senha = st.text_input("Senha", type="password", key="nova_senha")
        confirmar_senha = st.text_input("Confirmar senha", type="password", key="confirmar_senha")
        
        if st.button("Criar Conta"):
            if nova_senha != confirmar_senha:
                st.error("❌ As senhas não coincidem!")
            elif len(nova_senha) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres!")
            elif len(novo_username) < 3:
                st.error("❌ O nome de usuário deve ter pelo menos 3 caracteres!")
            else:
                if criar_usuario(novo_username, nova_senha, novo_nome):
                    st.success("✅ Conta criada com sucesso! Faça login na aba anterior.")
                else:
                    st.error("❌ Nome de usuário já existe!")

else:
    # --- Interface Principal ---
    usuarios = carregar_usuarios()
    nome_usuario = usuarios[st.session_state.usuario_logado]['nome_completo']
    
    # Header com informações do usuário
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"📊 Controle de Rendimentos - {nome_usuario}")
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.usuario_logado = None
            st.rerun()
    
    # --- Configuração de Meta Diária ---
    st.subheader("🎯 Meta Diária")
    
    meta_atual = obter_meta_diaria(st.session_state.usuario_logado)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        nova_meta = st.number_input("Defina sua meta diária (R$)", 
                                   value=meta_atual, 
                                   min_value=0.0, 
                                   format="%.2f")
    with col2:
        if st.button("💾 Salvar Meta"):
            salvar_meta_diaria(st.session_state.usuario_logado, nova_meta)
            st.success("✅ Meta salva!")
            st.rerun()
    
    # --- Mostrar Progresso da Meta de Hoje ---
    data_hoje = date.today()
    df_usuario = carregar_dados()
    if not df_usuario.empty:
        # Verificar se a coluna Usuario existe antes de filtrar
        if 'Usuario' in df_usuario.columns:
            df_usuario = df_usuario[df_usuario['Usuario'] == st.session_state.usuario_logado]
        else:
            # Se não existe coluna Usuario, assumir que todos os dados são do usuário atual
            df_usuario["Usuario"] = st.session_state.usuario_logado
        
        df_usuario["Data"] = pd.to_datetime(df_usuario["Data"], errors="coerce")
        df_usuario = df_usuario.dropna(subset=["Data"])
    
    if nova_meta > 0:
        rendimento_hoje, progresso, status = calcular_progresso_meta(df_usuario, data_hoje, nova_meta)
        
        st.subheader(f"📈 Progresso de Hoje ({data_hoje.strftime('%d/%m/%Y')})")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Meta Diária", f"R$ {nova_meta:.2f}")
        with col2:
            st.metric("Rendimento Hoje", f"R$ {rendimento_hoje:.2f}")
        with col3:
            st.metric("Progresso", f"{progresso:.1f}%")
        with col4:
            st.metric("Status", status)
        
        # Barra de progresso
        progress_bar = min(progresso / 100, 1.0)
        st.progress(progress_bar)
        
        # Gráfico de meta vs realizado
        fig_meta = go.Figure()
        fig_meta.add_trace(go.Bar(
            x=['Meta', 'Realizado'],
            y=[nova_meta, rendimento_hoje],
            marker_color=['lightblue', 'green' if rendimento_hoje >= nova_meta else 'orange'],
            text=[f'R$ {nova_meta:.2f}', f'R$ {rendimento_hoje:.2f}'],
            textposition='auto',
        ))
        fig_meta.update_layout(
            title=f"Meta vs Realizado - {data_hoje.strftime('%d/%m/%Y')}",
            yaxis_title="Valor (R$)",
            showlegend=False
        )
        st.plotly_chart(fig_meta, use_container_width=True)
    
    # --- Formulário para adicionar novo rendimento ---
    st.subheader("➕ Adicionar Rendimento")
    with st.form("form_rendimento_adicionar"):
        data = st.date_input("Data do rendimento", value=datetime.today())
        valor = st.number_input("Valor do rendimento (R$)", format="%.2f")
        enviado = st.form_submit_button("Adicionar rendimento")

        if enviado and valor != 0:
            df_atual = carregar_dados()
            novo_dado = pd.DataFrame({
                "Data": [data], 
                "Valor": [valor], 
                "Usuario": [st.session_state.usuario_logado]
            })
            df_atualizado = pd.concat([df_atual, novo_dado], ignore_index=True)
            
            if salvar_dados(df_atualizado):
                st.success("✅ Rendimento adicionado com sucesso!")
                st.session_state.dados_carregados = df_atualizado
                st.rerun()

    # --- Carregamento dos dados do usuário ---
    df = carregar_dados()
    if not df.empty:
        # Verificar se a coluna Usuario existe antes de filtrar
        if 'Usuario' in df.columns:
            df = df[df['Usuario'] == st.session_state.usuario_logado]
        else:
            # Se não existe coluna Usuario, assumir que todos os dados são do usuário atual
            df["Usuario"] = st.session_state.usuario_logado
        
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        df = df.sort_values("Data").reset_index(drop=True)

    if not df.empty:
        st.subheader("📅 Editar ou Excluir Rendimentos")

        df_editavel = df.copy()
        df_editavel["Excluir"] = False
        df_editavel = df_editavel[["Data", "Valor", "Excluir"]]  # Ocultar coluna Usuario

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

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Salvar alterações", key="salvar_alteracoes"):
                df_salvo = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
                df_salvo["Usuario"] = st.session_state.usuario_logado
                
                # Manter dados de outros usuários
                df_outros = carregar_dados()
                if not df_outros.empty:
                    # Verificar se existe coluna Usuario nos dados carregados
                    if 'Usuario' in df_outros.columns:
                        df_outros = df_outros[df_outros['Usuario'] != st.session_state.usuario_logado]
                    else:
                        # Se não existe coluna Usuario, criar para compatibilidade
                        df_outros["Usuario"] = "usuario_antigo"
                        df_outros = df_outros[df_outros['Usuario'] != st.session_state.usuario_logado]
                    
                    df_salvo = pd.concat([df_outros, df_salvo], ignore_index=True)
                
                df_salvo["Data"] = pd.to_datetime(df_salvo["Data"], errors="coerce")
                df_salvo = df_salvo.dropna(subset=["Data"])
                
                if salvar_dados(df_salvo):
                    st.success("✅ Alterações salvas com sucesso!")
                    st.session_state.dados_carregados = df_salvo
                    st.rerun()

        with col2:
            if st.button("🗑️ Excluir selecionados", key="excluir_selecionados"):
                itens_excluir = df_editado["Excluir"].sum()
                
                if itens_excluir > 0:
                    df_restante = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
                    df_restante["Usuario"] = st.session_state.usuario_logado
                    
                    # Manter dados de outros usuários
                    df_outros = carregar_dados()
                    if not df_outros.empty:
                        # Verificar se existe coluna Usuario nos dados carregados
                        if 'Usuario' in df_outros.columns:
                            df_outros = df_outros[df_outros['Usuario'] != st.session_state.usuario_logado]
                        else:
                            # Se não existe coluna Usuario, criar para compatibilidade
                            df_outros["Usuario"] = "usuario_antigo"
                            df_outros = df_outros[df_outros['Usuario'] != st.session_state.usuario_logado]
                        
                        if not df_restante.empty:
                            df_final = pd.concat([df_outros, df_restante], ignore_index=True)
                        else:
                            df_final = df_outros
                    else:
                        df_final = df_restante
                    
                    if salvar_dados(df_final):
                        st.success(f"✅ {itens_excluir} registro(s) excluído(s) com sucesso!")
                        st.session_state.dados_carregados = df_final
                        st.rerun()
                else:
                    st.warning("⚠️ Nenhum item selecionado para exclusão.")

        # --- Processar dados para resumos ---
        df_para_resumo = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
        
        if not df_para_resumo.empty:
            df_para_resumo["Data"] = pd.to_datetime(df_para_resumo["Data"], errors="coerce")
            df_para_resumo = df_para_resumo.dropna(subset=["Data"])
            
            df_para_resumo["Dia"] = df_para_resumo["Data"].dt.date
            df_para_resumo["Semana"] = df_para_resumo["Data"].dt.isocalendar().week
            df_para_resumo["Mês"] = df_para_resumo["Data"].dt.to_period("M").astype(str)

            # --- Resumo Diário com Meta ---
            resumo_dia = df_para_resumo.groupby("Dia")["Valor"].sum().reset_index()
            resumo_dia.columns = ["Data", "Total (R$)"]
            resumo_dia["Mês"] = resumo_dia["Data"].astype(str).str.slice(0, 7)
            resumo_dia["Meta Atingida"] = resumo_dia["Total (R$)"] >= nova_meta
            resumo_dia["Status"] = resumo_dia["Meta Atingida"].map({True: "✅", False: "❌"})

            if not resumo_dia.empty:
                meses_disponiveis = sorted(resumo_dia["Mês"].unique(), reverse=True)
                mes_selecionado = st.selectbox("Selecione o mês para ver o resumo diário", meses_disponiveis)

                resumo_dia_mes = resumo_dia[resumo_dia["Mês"] == mes_selecionado]

                st.subheader(f"📆 Resumo Diário de {mes_selecionado}")
                
                # Estatísticas do mês
                dias_meta_atingida = resumo_dia_mes["Meta Atingida"].sum()
                total_dias = len(resumo_dia_mes)
                percentual_sucesso = (dias_meta_atingida / total_dias) * 100 if total_dias > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Dias com Meta Atingida", f"{dias_meta_atingida}/{total_dias}")
                with col2:
                    st.metric("Taxa de Sucesso", f"{percentual_sucesso:.1f}%")
                with col3:
                    st.metric("Rendimento Total", f"R$ {resumo_dia_mes['Total (R$)'].sum():.2f}")
                
                # Tabela com status
                st.dataframe(
                    resumo_dia_mes[["Data", "Total (R$)", "Status"]].style.format({"Total (R$)": "R$ {:.2f}"}), 
                    use_container_width=True
                )

                # Gráfico com linha de meta
                fig_dia_mes = go.Figure()
                
                # Linha de rendimento
                fig_dia_mes.add_trace(go.Scatter(
                    x=resumo_dia_mes["Data"],
                    y=resumo_dia_mes["Total (R$)"],
                    mode='lines+markers',
                    name='Rendimento',
                    line=dict(color='blue'),
                    marker=dict(
                        color=['green' if x else 'red' for x in resumo_dia_mes["Meta Atingida"]],
                        size=8
                    )
                ))
                
                # Linha de meta
                if nova_meta > 0:
                    fig_dia_mes.add_hline(
                        y=nova_meta, 
                        line_dash="dash", 
                        line_color="red",
                        annotation_text=f"Meta: R$ {nova_meta:.2f}"
                    )
                
                fig_dia_mes.update_layout(
                    title=f"Rendimento Diário vs Meta - {mes_selecionado}",
                    yaxis_title="Total (R$)",
                    xaxis_title="Data",
                    xaxis_tickformat="%d/%m/%Y"
                )
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
        st.info("🔎 Nenhum rendimento registrado ainda.")
