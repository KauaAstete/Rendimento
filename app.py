import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

ARQUIVO_DADOS = "rendimentos.csv"

def carregar_dados():
    try:
        df = pd.read_csv(ARQUIVO_DADOS, parse_dates=["Data"])
        if "Data" not in df.columns or "Valor" not in df.columns:
            return pd.DataFrame(columns=["Data", "Valor"])
        return df
    except Exception:
        return pd.DataFrame(columns=["Data", "Valor"])

def salvar_dados(df):
    if not df.empty and {"Data", "Valor"}.issubset(df.columns):
        # Garantir que as datas são válidas antes de salvar
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

# Inicializar session state
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = carregar_dados()

# --- Título ---
st.title("📊 Controle de Rendimentos")

# --- Formulário para adicionar novo rendimento ---
with st.form("form_rendimento_adicionar"):
    data = st.date_input("Data do rendimento", value=datetime.today())
    valor = st.number_input("Valor do rendimento (R$)", format="%.2f")
    enviado = st.form_submit_button("Adicionar rendimento")

    if enviado and valor != 0:
        # Recarregar dados do arquivo para garantir consistência
        df_atual = carregar_dados()
        novo_dado = pd.DataFrame({"Data": [data], "Valor": [valor]})
        df_atualizado = pd.concat([df_atual, novo_dado], ignore_index=True)
        
        if salvar_dados(df_atualizado):
            st.success("✅ Rendimento adicionado com sucesso!")
            # Atualizar session state
            st.session_state.dados_carregados = df_atualizado
            st.rerun()

# --- Carregamento dos dados ---
df = carregar_dados()

if not df.empty:
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df = df.sort_values("Data").reset_index(drop=True)

    st.subheader("📅 Editar ou Excluir Rendimentos")

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

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salvar alterações", key="salvar_alteracoes"):
            # Filtrar dados não marcados para exclusão
            df_salvo = df_editado[df_editado["Excluir"] == False].drop(columns=["Excluir"])
            
            # Validar e limpar dados
            df_salvo = df_salvo.copy()
            df_salvo["Data"] = pd.to_datetime(df_salvo["Data"], errors="coerce")
            df_salvo = df_salvo.dropna(subset=["Data"])
            
            if not df_salvo.empty:
                if salvar_dados(df_salvo):
                    st.success("✅ Alterações salvas com sucesso!")
                    st.session_state.dados_carregados = df_salvo
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
                    if salvar_dados(df_restante):
                        st.success(f"✅ {itens_excluir} registro(s) excluído(s) com sucesso!")
                        st.session_state.dados_carregados = df_restante
                        st.rerun()
                else:
                    # Se não há dados restantes, criar arquivo vazio
                    df_vazio = pd.DataFrame(columns=["Data", "Valor"])
                    df_vazio.to_csv(ARQUIVO_DADOS, index=False)
                    st.success(f"✅ Todos os registros foram excluídos!")
                    st.session_state.dados_carregados = df_vazio
                    st.rerun()
            else:
                st.warning("⚠️ Nenhum item selecionado para exclusão.")

    # --- Processar dados para resumos (usar dados não marcados para exclusão) ---
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
    st.info("🔎 Nenhum rendimento registrado ainda.")
