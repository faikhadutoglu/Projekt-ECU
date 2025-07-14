#!/usr/bin/env python3
"""
RepoManager – Repository-Updater & JSON-Ausleser
Ein mächtiges Tool für Repository- und JSON-Datei-Management
"""
import sys
import os
import json
import re
import time
import requests
import base64
import fnmatch
from pathlib import Path

# ANSI-Farbcodes für die Konsole
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

# GitHub-Konfiguration
GITHUB_TOKEN = "..."  # Hier dein GitHub Token einfügen
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def clear_screen():
    """Bildschirm leeren"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Schönen Banner mit Farben ausgeben"""
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}🚀 RepoManager – Repository-Updater & JSON-Manager 🚀{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.GRAY}Ein mächtiges Tool für Repository- und JSON-Datei-Management{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")

def print_menu():
    """Menü mit Farben und Icons ausgeben"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}📋 HAUPTMENÜ{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    menu_items = [
        ("A", "🔍 JSON-Dateien analysieren", Colors.GREEN),
        ("B", "📝 Konfiguration bearbeiten", Colors.CYAN),
        ("C", "🔄 JSON-Werte updaten", Colors.YELLOW),
        ("D", "📊 Letzte Ergebnisse anzeigen", Colors.MAGENTA),
        ("E", "⚙️  GitHub Token konfigurieren", Colors.BLUE),
        ("F", "🚪 Exit", Colors.RED)
    ]
    
    for key, label, color in menu_items:
        print(f"{color}[{key}]{Colors.RESET} {label}")
    
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")

def load_config():
    """Konfiguration laden oder erstellen"""
    config_file = "config.json"
    
    # Standard-Konfiguration
    default_config = {
        "target_file": "build.json",
        "branch_pattern": "release/*",
        "repos": [
            "spx01/STLA.BSW.ZCU_CL",
            "spx01/STLA.BSW.ZCU_CR"
        ],
        "search_mode": "full",  # "full" oder "specific"
        "search_key": "",       # Spezifischer Schlüssel zum Suchen
        "search_value": ""      # Spezifischer Wert zum Suchen
    }
    
    # Wenn config.json nicht existiert, erstelle sie
    if not os.path.exists(config_file):
        try:
            with open(config_file, "w") as f:
                json.dump(default_config, f, indent=4)
            print(f"{Colors.GREEN}✅ Standard config.json erstellt{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}❌ Fehler beim Erstellen der config.json: {e}{Colors.RESET}")
            return default_config
    
    # Konfiguration laden
    try:
        with open(config_file) as f:
            config = json.load(f)
        # Fehlende Schlüssel mit Standardwerten ergänzen
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler beim Laden der config.json: {e}{Colors.RESET}")
        return default_config

def save_config(config):
    """Konfiguration speichern"""
    config_file = "config.json"
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler beim Speichern der config.json: {e}{Colors.RESET}")
        return False

def get_branches(owner, repo, limit=None):
    """Branches eines Repositories abrufen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/branches"
    branches = []
    page = 1
    per_page = 30

    while True:
        params = {"per_page": per_page, "page": page}
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code != 200:
            print(f"{Colors.RED}❌ Error fetching branches for {owner}/{repo}: {r.status_code} {r.text}{Colors.RESET}")
            break
        data = r.json()
        branches.extend([b["name"] for b in data])
        if len(data) < per_page or (limit and len(branches) >= limit):
            break
        page += 1

    return branches[:limit] if limit else branches

def get_file_content(owner, repo, path, branch):
    """Dateiinhalt von GitHub abrufen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        content = r.json()
        return base64.b64decode(content["content"]).decode(), content["sha"]
    return None, None

def search_in_json(json_content, search_key="", search_value=""):
    """JSON-Inhalt durchsuchen"""
    try:
        data = json.loads(json_content)
        results = {}
        
        if not search_key and not search_value:
            # Vollständige JSON-Struktur zurückgeben
            return data
        
        # Spezifische Suche
        def search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Schlüssel-Suche
                    if search_key and search_key.lower() in key.lower():
                        results[current_path] = value
                    
                    # Wert-Suche
                    if search_value and isinstance(value, str) and search_value.lower() in value.lower():
                        results[current_path] = value
                    
                    # Rekursiv weitersuchen
                    if isinstance(value, (dict, list)):
                        search_recursive(value, current_path)
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, (dict, list)):
                        search_recursive(item, current_path)
                    elif search_value and isinstance(item, str) and search_value.lower() in item.lower():
                        results[current_path] = item
        
        search_recursive(data)
        return results
        
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}❌ JSON-Fehler: {e}{Colors.RESET}")
        return None

def update_json_value(json_content, key_path, new_value):
    """JSON-Wert an spezifischem Pfad aktualisieren"""
    try:
        data = json.loads(json_content)
        
        # Pfad aufteilen (z.B. "MPU.AUTOSYNC" -> ["MPU", "AUTOSYNC"])
        keys = key_path.split('.')
        current = data
        
        # Bis zum vorletzten Schlüssel navigieren
        for key in keys[:-1]:
            if key in current and isinstance(current[key], dict):
                current = current[key]
            else:
                print(f"{Colors.RED}❌ Pfad nicht gefunden: {key_path}{Colors.RESET}")
                return None
        
        # Letzten Wert aktualisieren
        final_key = keys[-1]
        if final_key in current:
            old_value = current[final_key]
            current[final_key] = new_value
            print(f"{Colors.GREEN}✅ Aktualisiert: {key_path}{Colors.RESET}")
            print(f"  {Colors.YELLOW}Alt: {old_value}{Colors.RESET}")
            print(f"  {Colors.GREEN}Neu: {new_value}{Colors.RESET}")
            return json.dumps(data, indent=4)
        else:
            print(f"{Colors.RED}❌ Schlüssel nicht gefunden: {final_key}{Colors.RESET}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}❌ JSON-Fehler: {e}{Colors.RESET}")
        return None

def create_branch(owner, repo, base_branch, new_branch):
    """Neuen Branch erstellen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/git/refs/heads/{base_branch}"
    r = requests.get(url, headers=HEADERS)
    sha = r.json()["object"]["sha"]
    data = {"ref": f"refs/heads/{new_branch}", "sha": sha}
    requests.post(f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/git/refs", headers=HEADERS, json=data)

def update_file(owner, repo, path, content, sha, branch, message):
    """Datei in GitHub aktualisieren"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/contents/{path}"
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
        "branch": branch
    }
    requests.put(url, headers=HEADERS, json=data)

def create_pull_request(owner, repo, head, base, title, body):
    """Pull Request erstellen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/pulls"
    data = {"title": title, "head": head, "base": base, "body": body}
    r = requests.post(url, headers=HEADERS, json=data)
    return r.json()["html_url"]

def analyze_json_files():
    """JSON-Dateien in allen konfigurierten Repositories analysieren"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}🔍 JSON-DATEIEN ANALYSIEREN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    if not GITHUB_TOKEN or GITHUB_TOKEN == "...":
        print(f"{Colors.RED}❌ GitHub Token nicht konfiguriert!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Token in Option E konfigurieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    # Konfiguration laden
    config = load_config()
    target_file = config["target_file"]
    branch_pattern = config["branch_pattern"]
    repos = config["repos"]
    search_mode = config["search_mode"]
    search_key = config["search_key"]
    search_value = config["search_value"]
    
    print(f"{Colors.YELLOW}📋 Konfiguration:{Colors.RESET}")
    print(f"  Target File: {Colors.CYAN}{target_file}{Colors.RESET}")
    print(f"  Branch Pattern: {Colors.CYAN}{branch_pattern}{Colors.RESET}")
    print(f"  Search Mode: {Colors.CYAN}{search_mode}{Colors.RESET}")
    if search_mode == "specific":
        print(f"  Search Key: {Colors.CYAN}{search_key or 'N/A'}{Colors.RESET}")
        print(f"  Search Value: {Colors.CYAN}{search_value or 'N/A'}{Colors.RESET}")
    print(f"  Repositories: {Colors.CYAN}{len(repos)}{Colors.RESET}")
    
    output = {
        "target_file": target_file,
        "search_mode": search_mode,
        "search_key": search_key,
        "search_value": search_value,
        "results": {}
    }
    
    for repo_full in repos:
        print(f"\n{Colors.BOLD}🔄 Analysiere {repo_full}...{Colors.RESET}")
        owner, repo = repo_full.split("/")
        
        try:
            branches = get_branches(owner, repo)
            matching_branches = [b for b in branches if fnmatch.fnmatch(b, branch_pattern)]
            
            print(f"  {Colors.GREEN}✓ Gefundene Branches: {len(matching_branches)}{Colors.RESET}")
            
            output['results'][repo_full] = {}
            
            for branch in matching_branches:
                content, sha = get_file_content(owner, repo, target_file, branch)
                if not content:
                    print(f"    {Colors.RED}❌ {branch}: Datei nicht gefunden{Colors.RESET}")
                    output['results'][repo_full][branch] = {"error": "File not found"}
                    continue
                
                if search_mode == "full":
                    # Komplette JSON-Struktur analysieren
                    json_data = search_in_json(content)
                    if json_data:
                        output['results'][repo_full][branch] = json_data
                        print(f"    {Colors.GREEN}✓ {branch}: JSON-Struktur erfasst{Colors.RESET}")
                    else:
                        output['results'][repo_full][branch] = {"error": "Invalid JSON"}
                        print(f"    {Colors.RED}❌ {branch}: Ungültiges JSON{Colors.RESET}")
                
                elif search_mode == "specific":
                    # Spezifische Suche
                    search_results = search_in_json(content, search_key, search_value)
                    if search_results:
                        output['results'][repo_full][branch] = search_results
                        print(f"    {Colors.GREEN}✓ {branch}: {len(search_results)} Treffer{Colors.RESET}")
                    else:
                        output['results'][repo_full][branch] = {}
                        print(f"    {Colors.YELLOW}⚠️  {branch}: Keine Treffer{Colors.RESET}")
                
                time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"    {Colors.RED}❌ Fehler bei {repo_full}: {e}{Colors.RESET}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Ergebnisse speichern
    with open("output.json", "w") as f:
        json.dump(output, f, indent=4)
    
    print(f"\n{Colors.GREEN}✅ Analyse abgeschlossen!{Colors.RESET}")
    print(f"{Colors.CYAN}Ergebnisse in output.json gespeichert.{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def create_edit_config():
    """Config.json erstellen oder bearbeiten"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}📝 KONFIGURATION BEARBEITEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    # Aktuelle Konfiguration laden
    config = load_config()
    
    print(f"{Colors.YELLOW}📋 Aktuelle Konfiguration:{Colors.RESET}")
    print(f"  Target File: {Colors.CYAN}{config['target_file']}{Colors.RESET}")
    print(f"  Branch Pattern: {Colors.CYAN}{config['branch_pattern']}{Colors.RESET}")
    print(f"  Search Mode: {Colors.CYAN}{config['search_mode']}{Colors.RESET}")
    print(f"  Search Key: {Colors.CYAN}{config['search_key'] or 'N/A'}{Colors.RESET}")
    print(f"  Search Value: {Colors.CYAN}{config['search_value'] or 'N/A'}{Colors.RESET}")
    print(f"  Repositories: {Colors.CYAN}{len(config['repos'])}{Colors.RESET}")
    for i, repo in enumerate(config['repos'], 1):
        print(f"    {i}. {repo}")
    
    print(f"\n{Colors.YELLOW}Was möchten Sie bearbeiten?{Colors.RESET}")
    print(f"[1] Target File ändern")
    print(f"[2] Branch Pattern ändern")
    print(f"[3] Search Mode konfigurieren")
    print(f"[4] Repositories bearbeiten")
    print(f"[5] Alle Einstellungen zurücksetzen")
    print(f"[6] Zurück zum Hauptmenü")
    
    choice = input(f"Auswahl [6]: ").strip()
    
    if choice == "1":
        new_file = input(f"Neue Target File [{config['target_file']}]: ").strip()
        if new_file:
            config['target_file'] = new_file
            
    elif choice == "2":
        new_pattern = input(f"Neues Branch Pattern [{config['branch_pattern']}]: ").strip()
        if new_pattern:
            config['branch_pattern'] = new_pattern
            
    elif choice == "3":
        configure_search_mode(config)
        
    elif choice == "4":
        edit_repositories(config)
        
    elif choice == "5":
        confirm = input(f"{Colors.RED}Alle Einstellungen zurücksetzen? (ja/nein): {Colors.RESET}").strip().lower()
        if confirm in ['ja', 'yes', 'j', 'y']:
            config = {
                "target_file": "build.json",
                "branch_pattern": "release/*",
                "repos": [
                    "spx01/STLA.BSW.ZCU_CL",
                    "spx01/STLA.BSW.ZCU_CR"
                ],
                "search_mode": "full",
                "search_key": "",
                "search_value": ""
            }
            print(f"{Colors.GREEN}✅ Konfiguration zurückgesetzt{Colors.RESET}")
    
    elif choice == "6" or not choice:
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    # Konfiguration speichern
    if save_config(config):
        print(f"\n{Colors.GREEN}✅ Konfiguration gespeichert!{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}❌ Fehler beim Speichern!{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def configure_search_mode(config):
    """Search Mode konfigurieren"""
    print(f"\n{Colors.YELLOW}🔍 SEARCH MODE KONFIGURIEREN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*30}{Colors.RESET}")
    
    print(f"[1] Full - Komplette JSON-Struktur analysieren")
    print(f"[2] Specific - Nach spezifischen Schlüsseln/Werten suchen")
    
    choice = input(f"Auswahl: ").strip()
    
    if choice == "1":
        config['search_mode'] = "full"
        config['search_key'] = ""
        config['search_value'] = ""
        print(f"{Colors.GREEN}✅ Full Mode aktiviert{Colors.RESET}")
        
    elif choice == "2":
        config['search_mode'] = "specific"
        
        print(f"\n{Colors.YELLOW}Spezifische Suche konfigurieren:{Colors.RESET}")
        search_key = input(f"Schlüssel zum Suchen (leer für alle): ").strip()
        search_value = input(f"Wert zum Suchen (leer für alle): ").strip()
        
        config['search_key'] = search_key
        config['search_value'] = search_value
        
        print(f"{Colors.GREEN}✅ Specific Mode aktiviert{Colors.RESET}")
        if search_key:
            print(f"  Search Key: {search_key}")
        if search_value:
            print(f"  Search Value: {search_value}")

def edit_repositories(config):
    """Repository-Liste bearbeiten"""
    while True:
        print(f"\n{Colors.YELLOW}📦 REPOSITORY-VERWALTUNG{Colors.RESET}")
        print(f"{Colors.BLUE}{'─'*30}{Colors.RESET}")
        
        print(f"{Colors.YELLOW}Aktuelle Repositories:{Colors.RESET}")
        for i, repo in enumerate(config['repos'], 1):
            print(f"  {i}. {repo}")
        
        print(f"\n{Colors.YELLOW}Optionen:{Colors.RESET}")
        print(f"[1] Repository hinzufügen")
        print(f"[2] Repository entfernen")
        print(f"[3] Repository bearbeiten")
        print(f"[4] Alle Repositories löschen")
        print(f"[5] Fertig")
        
        choice = input(f"Auswahl [5]: ").strip()
        
        if choice == "1":
            new_repo = input(f"Neues Repository (org/name): ").strip()
            if new_repo and "/" in new_repo:
                if new_repo not in config['repos']:
                    config['repos'].append(new_repo)
                    print(f"{Colors.GREEN}✅ Repository {new_repo} hinzugefügt{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}⚠️  Repository bereits vorhanden{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Ungültiges Format! Verwende: org/name{Colors.RESET}")
                
        elif choice == "2":
            if not config['repos']:
                print(f"{Colors.YELLOW}⚠️  Keine Repositories vorhanden{Colors.RESET}")
                continue
                
            try:
                index = int(input(f"Repository-Nummer zum Entfernen (1-{len(config['repos'])}): ")) - 1
                if 0 <= index < len(config['repos']):
                    removed = config['repos'].pop(index)
                    print(f"{Colors.GREEN}✅ Repository {removed} entfernt{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ Ungültige Nummer{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}❌ Bitte eine Zahl eingeben{Colors.RESET}")
                
        elif choice == "3":
            if not config['repos']:
                print(f"{Colors.YELLOW}⚠️  Keine Repositories vorhanden{Colors.RESET}")
                continue
                
            try:
                index = int(input(f"Repository-Nummer zum Bearbeiten (1-{len(config['repos'])}): ")) - 1
                if 0 <= index < len(config['repos']):
                    old_repo = config['repos'][index]
                    new_repo = input(f"Neuer Name für {old_repo}: ").strip()
                    if new_repo and "/" in new_repo:
                        config['repos'][index] = new_repo
                        print(f"{Colors.GREEN}✅ Repository geändert: {old_repo} → {new_repo}{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}❌ Ungültiges Format! Verwende: org/name{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ Ungültige Nummer{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}❌ Bitte eine Zahl eingeben{Colors.RESET}")
                
        elif choice == "4":
            confirm = input(f"{Colors.RED}Alle Repositories löschen? (ja/nein): {Colors.RESET}").strip().lower()
            if confirm in ['ja', 'yes', 'j', 'y']:
                config['repos'] = []
                print(f"{Colors.GREEN}✅ Alle Repositories entfernt{Colors.RESET}")
                
        elif choice == "5" or not choice:
            break

def update_json_values():
    """JSON-Werte updaten und Pull Requests erstellen"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}🔄 JSON-WERTE UPDATEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    if not GITHUB_TOKEN or GITHUB_TOKEN == "...":
        print(f"{Colors.RED}❌ GitHub Token nicht konfiguriert!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Token in Option E konfigurieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    output_file = "output.json"
    if not os.path.exists(output_file):
        print(f"{Colors.RED}❌ output.json nicht gefunden!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst JSON-Dateien in Option A analysieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    # Update-Konfiguration eingeben
    print(f"{Colors.YELLOW}Update-Konfiguration:{Colors.RESET}")
    key_path = input(f"JSON-Pfad (z.B. MPU.AUTOSYNC oder PROJECT_NAME): ").strip()
    if not key_path:
        print(f"{Colors.RED}❌ Kein Pfad eingegeben!{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    new_value = input(f"Neuer Wert: ").strip()
    if not new_value:
        print(f"{Colors.RED}❌ Kein Wert eingegeben!{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    # Wert-Typ bestimmen
    print(f"\n{Colors.YELLOW}Wert-Typ:{Colors.RESET}")
    print(f"[1] String (Text)")
    print(f"[2] Number (Zahl)")
    print(f"[3] Boolean (true/false)")
    
    value_type = input(f"Typ [1]: ").strip()
    
    if value_type == "2":
        try:
            new_value = float(new_value) if '.' in new_value else int(new_value)
        except ValueError:
            print(f"{Colors.RED}❌ Ungültige Zahl!{Colors.RESET}")
            input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
            return
    elif value_type == "3":
        new_value = new_value.lower() in ['true', '1', 'yes', 'ja']
    
    try:
        with open(output_file) as f:
            results = json.load(f)
        
        target_file = results["target_file"]
        list_of_prs = []
        
        print(f"\n{Colors.YELLOW}🔄 Aktualisiere {key_path} = {new_value}{Colors.RESET}")
        
        for repo_full, branches_data in results['results'].items():
            if not branches_data:
                print(f"{Colors.GRAY}⏭️  {repo_full}: Keine Daten gefunden{Colors.RESET}")
                continue
            
            print(f"\n{Colors.BOLD}🔄 Bearbeite {repo_full}...{Colors.RESET}")
            
            for branch, branch_data in branches_data.items():
                if "error" in branch_data:
                    print(f"  {Colors.RED}❌ {branch}: {branch_data['error']}{Colors.RESET}")
                    continue
                
                try:
                    pr_branch = f"update-json-{key_path.replace('.', '-')}-{branch}"
                    owner, repo = repo_full.split("/")
                    
                    print(f"  {Colors.YELLOW}🔄 {branch}: Aktualisiere {key_path}{Colors.RESET}")
                    
                    # Aktuelle Datei abrufen
                    content, sha = get_file_content(owner, repo, target_file, branch)
                    if not content:
                        print(f"    {Colors.RED}❌ Datei nicht gefunden{Colors.RESET}")
                        continue
                    
                    # JSON aktualisieren
                    updated_content = update_json_value(content, key_path, new_value)
                    if not updated_content:
                        print(f"    {Colors.RED}❌ Update fehlgeschlagen{Colors.RESET}")
                        continue
                    
                    # Branch erstellen
                    create_branch(owner, repo, branch, pr_branch)
                    
                    # Datei aktualisieren
                    update_file(owner, repo, target_file, updated_content, sha, pr_branch,
                                f"Update {key_path} to {new_value}")
                    
                    # Pull Request erstellen
                    pr_url = create_pull_request(
                        owner, repo, pr_branch, branch,
                        f"Update {key_path} to {new_value}",
                        f"This PR updates {key_path} to {new_value} in {target_file}."
                    )
                    
                    print(f"    {Colors.GREEN}✅ PR erstellt: {pr_url}{Colors.RESET}")
                    list_of_prs.append(pr_url)
                    
                except Exception as e:
                    print(f"    {Colors.RED}❌ Fehler: {e}{Colors.RESET}")
                
                time.sleep(1)  # Rate limiting
            
            time.sleep(1)  # Rate limiting
        
        # PR-Liste speichern
        if list_of_prs:
            with open("created_prs.txt", "w") as f:
                for pr in list_of_prs:
                    f.write(f"{pr}\n")
            
            print(f"\n{Colors.GREEN}✅ {len(list_of_prs)} Pull Requests erstellt!{Colors.RESET}")
            print(f"{Colors.CYAN}Liste gespeichert in: created_prs.txt{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Keine Pull Requests erstellt.{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def show_last_results():
    """Letzte Ergebnisse anzeigen"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}📊 LETZTE ERGEBNISSE ANZEIGEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    output_file = "output.json"
    if not os.path.exists(output_file):
        print(f"{Colors.RED}❌ Keine Ergebnisse gefunden!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst JSON-Dateien in Option A analysieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    try:
        with open(output_file) as f:
            results = json.load(f)
        
        print(f"{Colors.YELLOW}📋 Analyse-Ergebnisse:{Colors.RESET}")
        print(f"  Target File: {Colors.CYAN}{results['target_file']}{Colors.RESET}")
        print(f"  Search Mode: {Colors.CYAN}{results['search_mode']}{Colors.RESET}")
        if results['search_mode'] == 'specific':
            print(f"  Search Key: {Colors.CYAN}{results['search_key'] or 'N/A'}{Colors.RESET}")
            print(f"  Search Value: {Colors.CYAN}{results['search_value'] or 'N/A'}{Colors.RESET}")
        
        for repo_full, branches_data in results['results'].items():
            print(f"\n{Colors.BOLD}📦 {repo_full}:{Colors.RESET}")
            
            if not branches_data:
                print(f"  {Colors.RED}❌ Keine Daten{Colors.RESET}")
                continue
            
            for branch, branch_data in branches_data.items():
                print(f"\n  {Colors.CYAN}🌿 {branch}:{Colors.RESET}")
                
                if "error" in branch_data:
                    print(f"    {Colors.RED}❌ {branch_data['error']}{Colors.RESET}")
                    continue
                
                if results['search_mode'] == 'full':
                    # Vollständige JSON-Struktur anzeigen (verkürzt)
                    print(f"    {Colors.GREEN}✅ JSON-Struktur erfasst{Colors.RESET}")
                    if isinstance(branch_data, dict):
                        for key, value in list(branch_data.items())[:5]:  # Nur erste 5 Einträge
                            if isinstance(value, (dict, list)):
                                print(f"      {Colors.YELLOW}{key}{Colors.RESET}: {type(value).__name__} ({len(value)} items)")
                            else:
                                print(f"      {Colors.YELLOW}{key}{Colors.RESET}: {value}")
                        if len(branch_data) > 5:
                            print(f"      {Colors.GRAY}... und {len(branch_data) - 5} weitere{Colors.RESET}")
                
                elif results['search_mode'] == 'specific':
                    # Spezifische Suchergebnisse anzeigen
                    if branch_data:
                        print(f"    {Colors.GREEN}✅ {len(branch_data)} Treffer:{Colors.RESET}")
                        for path, value in branch_data.items():
                            print(f"      {Colors.YELLOW}{path}{Colors.RESET}: {value}")
                    else:
                        print(f"    {Colors.YELLOW}⚠️  Keine Treffer{Colors.RESET}")
        
        # PR-Liste anzeigen falls vorhanden
        pr_file = "created_prs.txt"
        if os.path.exists(pr_file):
            print(f"\n{Colors.BOLD}{Colors.GREEN}📋 Erstellte Pull Requests:{Colors.RESET}")
            with open(pr_file) as f:
                prs = f.read().strip().split('\n')
                for i, pr in enumerate(prs, 1):
                    if pr.strip():
                        print(f"  {i}. {Colors.CYAN}{pr}{Colors.RESET}")
        
        # Detailansicht anbieten
        print(f"\n{Colors.YELLOW}Möchten Sie eine detaillierte Ansicht eines Branches?{Colors.RESET}")
        detail_choice = input(f"Repository/Branch (z.B. spx01/STLA.BSW.ZCU_CL/release/1.0) oder Enter zum Beenden: ").strip()
        
        if detail_choice:
            show_detailed_view(results, detail_choice)
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler beim Lesen der Ergebnisse: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def show_detailed_view(results, path):
    """Detaillierte Ansicht für spezifischen Branch"""
    try:
        parts = path.split('/')
        if len(parts) >= 3:
            repo_full = '/'.join(parts[:2])
            branch = '/'.join(parts[2:])
            
            if repo_full in results['results'] and branch in results['results'][repo_full]:
                branch_data = results['results'][repo_full][branch]
                
                print(f"\n{Colors.BOLD}🔍 DETAILANSICHT: {repo_full} / {branch}{Colors.RESET}")
                print(f"{Colors.BLUE}{'─'*60}{Colors.RESET}")
                
                if "error" in branch_data:
                    print(f"{Colors.RED}❌ {branch_data['error']}{Colors.RESET}")
                    return
                
                # JSON formatiert ausgeben
                print(json.dumps(branch_data, indent=2, ensure_ascii=False))
            else:
                print(f"{Colors.RED}❌ Pfad nicht gefunden: {path}{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Ungültiger Pfad. Format: org/repo/branch{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler: {e}{Colors.RESET}")

def configure_github_token():
    """GitHub Token konfigurieren"""
    global GITHUB_TOKEN, HEADERS
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}⚙️  GITHUB TOKEN KONFIGURIEREN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    print(f"{Colors.YELLOW}📋 Benötigte Berechtigungen:{Colors.RESET}")
    print(f"  • gist")
    print(f"  • project")
    print(f"  • repo")
    print(f"  • user")
    
    current_status = "✅ Konfiguriert" if GITHUB_TOKEN and GITHUB_TOKEN != "..." else "❌ Nicht konfiguriert"
    print(f"\n{Colors.YELLOW}Aktueller Status: {current_status}{Colors.RESET}")
    
    new_token = input(f"\n{Colors.YELLOW}Neuen GitHub Token eingeben (oder Enter zum Abbrechen): {Colors.RESET}").strip()
    
    if new_token:
        GITHUB_TOKEN = new_token
        HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        print(f"\n{Colors.GREEN}✅ Token aktualisiert!{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Hinweis: Token wird nur für diese Session gespeichert.{Colors.RESET}")
        print(f"{Colors.YELLOW}   Für permanente Speicherung bitte im Skript eintragen.{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}Token-Konfiguration abgebrochen.{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def exit_program():
    """Programm beenden"""
    print(f"\n{Colors.BOLD}{Colors.RED}🚪 PROGRAMM BEENDEN{Colors.RESET}")
    print(f"{Colors.GREEN}Auf Wiedersehen! 👋{Colors.RESET}")
    print(f"{Colors.CYAN}Danke für die Nutzung des RepoManagers!{Colors.RESET}")
    sys.exit(0)

# Aktionen-Dictionary
ACTIONS = {
    "A": ("JSON-Dateien analysieren", analyze_json_files),
    "B": ("Konfiguration bearbeiten", create_edit_config),
    "C": ("JSON-Werte updaten", update_json_values),
    "D": ("Letzte Ergebnisse anzeigen", show_last_results),
    "E": ("GitHub Token konfigurieren", configure_github_token),
    "F": ("Exit", exit_program),
}

def get_user_choice():
    """Benutzereingabe mit Farbunterstützung"""
    while True:
        choice = input(f"\n{Colors.BOLD}{Colors.WHITE}Bitte Auswahl eingeben: {Colors.RESET}").strip().upper()
        
        if choice in ACTIONS:
            return choice
        else:
            print(f"{Colors.RED}❌ Ungültige Auswahl!{Colors.RESET}")
            print(f"{Colors.YELLOW}Bitte A, B, C, D, E oder F eingeben.{Colors.RESET}")

def main() -> None:
    """Hauptfunktion"""
    try:
        while True:
            clear_screen()
            print_banner()
            print_menu()
            
            choice = get_user_choice()
            _, func = ACTIONS[choice]
            
            clear_screen()
            func()
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Programm wurde durch Benutzer abgebrochen.{Colors.RESET}")
        print(f"{Colors.GREEN}Auf Wiedersehen! 👋{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Ein Fehler ist aufgetreten: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()