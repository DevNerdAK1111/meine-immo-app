import streamlit as st
from supabase import Client

def get_supabase_client() -> Client:
    sb_url = st.secrets.get("SUPABASE_URL", "") or st.session_state.get("supabase_url", "")
    sb_key = st.secrets.get("SUPABASE_KEY", "") or st.session_state.get("supabase_key", "")
    if sb_url and sb_key:
        try:
            from supabase import create_client
            return create_client(sb_url, sb_key)
        except Exception:
            return None
    return None

def db_save_project(supabase: Client, user_id: str, project_name: str, payload: dict):
    if "local_projects" not in st.session_state:
        st.session_state["local_projects"] = []
    
    existing_local = next((p for p in st.session_state["local_projects"] if p["project_name"] == project_name), None)
    if existing_local:
        existing_local["input_data"] = payload
    else:
        st.session_state["local_projects"].append({
            "id": f"local_{len(st.session_state['local_projects'])+1}",
            "user_id": user_id,
            "project_name": project_name,
            "input_data": payload
        })

    if not supabase:
        return True, "Projekt lokal gesichert."

    try:
        res = supabase.table("projects").select("id").eq("user_id", user_id).eq("project_name", project_name).execute()
        if res.data and len(res.data) > 0:
            pid = res.data[0]["id"]
            supabase.table("projects").update({"input_data": payload}).eq("id", pid).execute()
        else:
            supabase.table("projects").insert({
                "user_id": user_id,
                "project_name": project_name,
                "input_data": payload
            }).execute()
        return True, "Projekt erfolgreich in der Datenbank gespeichert."
    except Exception as e:
        return False, f"Cloud-Sync Hinweis ({e}). Lokal gesichert."

def db_get_projects(supabase: Client, user_id: str):
    cloud_projects = []
    if supabase:
        try:
            res = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            cloud_projects = res.data or []
        except Exception:
            pass
            
    local_projects = st.session_state.get("local_projects", [])
    seen = set()
    combined = []
    for p in cloud_projects:
        name = p.get("project_name")
        if name not in seen:
            seen.add(name)
            combined.append(p)
    for p in local_projects:
        name = p.get("project_name")
        if name not in seen:
            seen.add(name)
            combined.append(p)
    return combined

def db_delete_project(supabase: Client, project_id):
    if "local_projects" in st.session_state:
        st.session_state["local_projects"] = [p for p in st.session_state["local_projects"] if str(p.get("id")) != str(project_id)]
    if supabase and not str(project_id).startswith("local_"):
        try:
            supabase.table("projects").delete().eq("id", project_id).execute()
        except Exception:
            pass
