# suivi_graissage_app.py
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import warnings


class GraissageManager:
    def __init__(self, excel_file):
        self.today = datetime.now().date()
        self.sheets = {}
        xls = pd.ExcelFile(excel_file)

        for sheet in xls.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet, header=1)
            df.columns = [str(col).strip().lower() for col in df.columns]
            self.mettre_a_jour_suivi(df)
            self.sheets[sheet] = df

    @staticmethod
    def parse_frequency(freq_str):
        freq_str = str(freq_str).lower().strip()
        if "1 fois/mois" in freq_str:
            return 30
        elif "1 fois/sem" in freq_str:
            return 7
        elif "1 fois/2mois" in freq_str:
            return 60
        elif "1 fois/45jours" in freq_str:
            return 45
        elif "1 fois/an" in freq_str:
            return 365
        elif "2 fois/an" in freq_str:
            return 182
        elif "3 fois/an" in freq_str:
            return 120
        elif "1 fois/2ans" in freq_str:
            return 730
        elif "décembre" in freq_str:
            return 'decembre'
        elif "janvier" in freq_str:
            return 'janvier'
        else:
            warnings.warn(f"Fréquence non reconnue: {freq_str}. Valeur par défaut 30 jours.")
            return 30

    def calculate_next_intervention(self, row, subtract_once=False):
        last_col = 'derniere intervention'
        freq_col = 'frequence'

        last_interv = row.get(last_col)
        if pd.isna(last_interv) or str(last_interv).strip() in ['******', '', 'niveau d\'huile vide']:
            return "Date indéterminée"

        try:
            last_date = pd.to_datetime(last_interv).date()
        except:
            return "Format de date invalide"

        freq_value = self.parse_frequency(row.get(freq_col, ''))

        if freq_value == 'decembre':
            next_date = datetime(last_date.year, 12, 1).date()
            while next_date < self.today:
                next_date = datetime(next_date.year + 1, 12, 1).date()
            return next_date
        elif freq_value == 'janvier':
            next_date = datetime(last_date.year, 1, 1).date()
            while next_date < self.today:
                next_date = datetime(next_date.year + 1, 1, 1).date()
            return next_date
        elif isinstance(freq_value, int):
            if subtract_once:
                # Soustraire une fois la fréquence
                next_date = last_date - timedelta(days=freq_value)
                # Ajuster si c'est un dimanche
                if next_date.weekday() == 6:
                    next_date -= timedelta(days=1)
                return next_date
            else:
                # Comportement normal - ajouter jusqu'à future
                next_date = last_date
                while next_date < self.today:
                    next_date += timedelta(days=freq_value)
                    # Ajuster si c'est un dimanche
                    if next_date.weekday() == 6:
                        next_date += timedelta(days=1)
                return next_date
        else:
            return "Fréquence non reconnue"

    def mettre_a_jour_suivi(self, df):
        for i, row in df.iterrows():
            derniere = row.get('derniere intervention')
            prochaine = row.get('prochaine intervention')

            try:
                derniere_date = pd.to_datetime(derniere).date() if not pd.isna(derniere) else None
                prochaine_date = pd.to_datetime(prochaine).date() if not pd.isna(prochaine) else None

                if derniere_date and prochaine_date and derniere_date == prochaine_date:
                    # Si les dates sont identiques, soustraire une fois la fréquence
                    df.at[i, 'prochaine intervention'] = self.calculate_next_intervention(row, subtract_once=True)
                else:
                    # Sinon calculer normalement
                    df.at[i, 'prochaine intervention'] = self.calculate_next_intervention(row)
            except:
                df.at[i, 'prochaine intervention'] = "Format de date invalide"

    def check_alerts(self):
        alerts = []
        for name, df in self.sheets.items():
            for _, row in df.iterrows():
                prochaine = row.get('prochaine intervention')
                if str(prochaine).lower().strip() in ['date indéterminée', '', '******']:
                    continue
                try:
                    prochaine_date = pd.to_datetime(prochaine).date()
                    days_left = (prochaine_date - self.today).days
                    if days_left <= 2:
                        alerts.append({
                            'Machine': name,
                            'Équipement': row.get('equipement') or row.get('équipement'),
                            'Type': row.get('type intervention') or row.get("type d'intervention"),
                            'Huile/Graisse': row.get('type de graisse /huile'),
                            'Date prévue': prochaine_date,
                            'Jours restants': days_left,
                            'Emplacement': row.get('emplacement')
                        })
                except:
                    continue
        return alerts


# === APP STREAMLIT ===
def main():
    st.set_page_config(page_title="Suivi Graissage", layout="wide")
    st.title("📃 Suivi de Graissage Automatisé - International Paper")

    uploaded_file = st.file_uploader("📄 Importer le fichier Excel de planification", type=["xlsx"])
    if uploaded_file:
        manager = GraissageManager(uploaded_file)

        tabs = st.tabs([f"📊 {name}" for name in manager.sheets.keys()] + ["🚨 Alertes"])

        for i, (name, df) in enumerate(manager.sheets.items()):
            with tabs[i]:
                st.subheader(f"Machine : {name}")
                st.dataframe(df, use_container_width=True)

        with tabs[-1]:
            alerts = manager.check_alerts()
            if alerts:
                st.warning(f"⚠️ {len(alerts)} interventions prévues sous 2 jours !")
                for alert in alerts:
                    with st.expander(f"🛠️ {alert['Machine']} | {alert['Équipement']} | ⏰ J-{alert['Jours restants']}"):
                        st.write(f"📍 Emplacement : {alert['Emplacement']}")
                        st.write(f"🛢️ Huile / Graisse : {alert['Huile/Graisse']}")
                        st.write(f"📅 Date prévue : {alert['Date prévue']}")
            else:
                st.success("🎉 Aucune intervention urgente dans les 2 prochains jours !")


if __name__ == "__main__":
    main()