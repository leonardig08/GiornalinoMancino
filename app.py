import streamlit as st
import streamlit_authenticator as stauth



def create_credentials(data):
    data = data.to_dict(orient="records")
    credentials = {}

    for row in data:
        credentials[row["user_id"]] = {
                "email": row["email"],
                "failed_login_attempts": row["failed_login_attempts"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "logged_in": row["logged_in"],
                "password": row["password"],
                "roles": row["user_roles"].split(","),
            }

    return credentials

def sync_data(conn, con):
    """
    Sincronizza il DB 'utente' con l'oggetto di configurazione 'con'.
    'con' deve avere la struttura: {"credentials": {"usernames": {...}}}
    """
    # Leggi dati attuali dal DB
    df = conn.query("SELECT * FROM utente")
    db_conf = create_credentials(df)  # dict user_id -> dati

    # Struttura conf dal DB (come se fosse generate_config)
    conf = {"usernames": db_conf}

    # Struttura locale (quella che vogliamo sincronizzare)
    conflocal = con["credentials"]["usernames"]

    # --- 1. UPDATE e INSERT ---
    for user_id, user_data in conflocal.items():
        if user_id in conf["usernames"]:
            # UPDATE solo se cambia qualcosa
            updates = []
            db_data = conf["usernames"][user_id]
            for key in ["email", "first_name", "last_name", "password", "logged_in", "failed_login_attempts", "roles"]:
                if key == "roles":
                    db_val = ",".join(db_data.get("roles", []))
                    local_val = ",".join(user_data.get("roles", []))
                    if db_val != local_val:
                        updates.append(f"user_roles = '{local_val}'")
                else:
                    db_val = db_data.get(key)
                    local_val = user_data.get(key)
                    if db_val != local_val:
                        updates.append(f"{key} = '{local_val}'")
            if updates:
                sql = f"UPDATE utente SET {', '.join(updates)} WHERE user_id = '{user_id}'"
                conn.query(sql)
        else:
            # INSERT nuovo utente
            columns = ["user_id", "email", "first_name", "last_name", "password", "logged_in", "failed_login_attempts", "user_roles"]
            values = [
                user_id,
                user_data.get("email", ""),
                user_data.get("first_name", ""),
                user_data.get("last_name", ""),
                user_data.get("password", ""),
                user_data.get("logged_in", 0),
                user_data.get("failed_login_attempts", 0),
                ",".join(user_data.get("roles", []))
            ]
            val_str = ",".join([f"'{v}'" for v in values])
            sql = f"INSERT INTO utente ({', '.join(columns)}) VALUES ({val_str})"
            conn.query(sql)

    # --- 2. DELETE utenti rimossi dal config locale ---
    db_user_ids = set(conf["usernames"].keys())
    local_user_ids = set(conflocal.keys())
    to_delete = db_user_ids - local_user_ids
    for uid in to_delete:
        conn.query(f"DELETE FROM utente WHERE user_id = '{uid}'")



def generate_config(credentials):
    con = {"credentials": {"usernames":credentials}, "cookie": st.secrets.get("cookie")}
    return con


conn = st.connection('mysql', type="sql")




df = conn.query("SELECT * FROM utente")
creds = create_credentials(df)
config = generate_config(creds)

authenticator = stauth.Authenticate(config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"])

try:
    authenticator.login(captcha=True)
except Exception as e:
    st.error(e)



