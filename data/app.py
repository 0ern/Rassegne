import os
import datetime
import time
import feedparser
import ollama
import re

# Color constants
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[34m'
DARK_GREY = '\033[90m'
ITALIC = '\033[3m'
RESET = '\033[0m'
BLINK = '\033[5m'

# VARIABILI MODIFICABILI
nome_modello = "llama3.1:8b" # (Llama 3 , Gemma 4)
model_code = 'llama3.1:8b'
file_fonti = "Fonti.txt"
prompt_ia = "Prompt_IA.txt"
output_folder = "Rassegne"

def main():
    # 1. Controllo se il file delle fonti esiste
    if not os.path.exists(file_fonti):
        print("{RED}Errore: Il file {file_fonti} non esiste. Crealo e inserisci i feed RSS.{RESET}")
        return

    with open(file_fonti, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("{YELLOW}Nessun link trovato in {file_fonti}.{RESET}")
        return

    print(f"{DARK_GREY}Lettura di {len(urls)} fonti in corso.{RESET}")

    # 2. Impostiamo il filtro temporale (Ultime 24 ore)
    ora_attuale = datetime.datetime.now(datetime.timezone.utc)
    ventiquattro_ore_fa = ora_attuale - datetime.timedelta(hours=24) # Impostare qui le ore di notizie da analizzare
    notizie_raccolte = []

    # 3. Estrazione notizie dai feed RSS
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Recuperiamo la data di pubblicazione dell'articolo
                data_articolo = entry.get('published_parsed') or entry.get('updated_parsed')
                if data_articolo:
                    dt = datetime.datetime.fromtimestamp(time.mktime(data_articolo), datetime.timezone.utc)
                    # Se l'articolo e' delle ultime 24 ore, lo salviamo
                    if dt >= ventiquattro_ore_fa:
                        notizie_raccolte.append({
                            "title": entry.get('title', 'Nessun titolo'),
                            "link": entry.get('link', '#'),
                            "summary": entry.get('summary', 'Nessun sommario disponibile.')
                            })
        except Exception as e:
            print(f"{RED}Impossibile leggere la fonte {url}: {e} {RESET}")
            
    if not notizie_raccolte:
        print("Non ci sono notizie pubblicate nelle ultime 24 ore nei tuoi feed.")
        return

    print(f"{DARK_GREY}Trovate {len(notizie_raccolte)} notizie.\nConnessione a Ollama modello {nome_modello} {RESET}")

    # 4. Gestione del Modello IA
    try:
        ollama.show(nome_modello)
    except Exception:
        print(f"{YELLOW}Modello '{nome_modello}' non trovato. Download in corso (solo per la prima volta, attendere)...{RESET}")
        try:
            ollama.pull(nome_modello)
        except Exception:
            print("{RED}Errore: Ollama non risponde. Assicurati che l'app Ollama sia aperta sul PC!{RESET}")
            return

    # 5. Caricamento del prompt esterno e preparazione dei dati
    if not os.path.exists(prompt_ia):
        print("{RED}Errore: Il file Prompt_IA.txt non esiste nella cartella.{RESET}")
        return

    with open(prompt_ia, "r", encoding="utf-8") as f:
        prompt_base = f.read()

    # --- CONFIGURAZIONE ELABORAZIONE A BLOCCHI (BATCHING) ---
    dimensione_batch = 5  # Elabora massimo 5 notizie alla volta per garantire precisione assoluta
    totale_notizie = len(notizie_raccolte)
    
    # Questo dizionario conterrà tutti i riassunti divisi per topic
    # Struttura: {"Economia": ["testo blocco 1", "testo blocco 2"], "Lavoro": [...]}
    rassegna_per_topic = {}    
    print(f"{BLINK}Elaborazione...{RESET}")

    # 6. Fase di Analisi (Map): l'IA elabora i piccoli gruppi
    for i in range(0, totale_notizie, dimensione_batch):
        batch_corrente = notizie_raccolte[i:i+dimensione_batch]
        numero_blocco = (i // dimensione_batch) + 1
        totale_blocchi = -(-totale_notizie // dimensione_batch)
        
        # print(f"Analisi blocco {numero_blocco} di {totale_blocchi}...")
        
        testo_per_ia = ""
        for idx_relativo, notizia in enumerate(batch_corrente):
            idx_assoluto = i + idx_relativo
            testo_per_ia += f"TAG_DA_COPIARE: [Link:{idx_assoluto}]\nTitolo: {notizia['title']}\nDescrizione: {notizia['summary']}\n\n"
            
        prompt = f"{prompt_base}\n\nEcco le notizie da elaborare:\n{testo_per_ia}"
        
        try:
            response = ollama.chat(
                model=model_code,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0, 'num_ctx': 8192}
            )
            testo_blocco = response['message']['content']
            
            # Sostituzione dei link markdown per questo blocco
            for idx_relativo, notizia in enumerate(batch_corrente):
                idx_assoluto = i + idx_relativo
                pattern = rf"\[\s*[Ll]ink\s*:\s*{idx_assoluto}\s*\]\.?"
                link_markdown = f"[{notizia['title']}]({notizia['link']}).\n\n"
                testo_blocco = re.sub(pattern, link_markdown, testo_blocco)
                
            # --- SEPARAZIONE INTELLIGENTE DEI TOPIC ---
            # Tagliamo il testo restituito dall'IA ogni volta che incontra un "## "
            parti_topic = testo_blocco.split("## ")
            for parte in parti_topic:
                if not parte.strip():
                    continue
                
                # La prima riga del blocco è il nome del Topic (es. "Economia"), il resto è il testo
                linee = parte.split("\n")
                nome_topic = linee[0].strip()
                contenuto_topic = "\n".join(linee[1:]).strip()
                
                if contenuto_topic:
                    # Se il topic non esiste nel dizionario, lo creiamo
                    if nome_topic not in rassegna_per_topic:
                        rassegna_per_topic[nome_topic] = []
                    # Appendiamo il testo a quel determinato topic
                    rassegna_per_topic[nome_topic].append(contenuto_topic)
            
        except Exception as e:
            print(f"{RED}[ERRORE] Salto il blocco {numero_blocco} per un problema tecnico: {e} {RESET}")
    
    testo_elaborato = ""    
    for topic, contenuti in rassegna_per_topic.items():
        testo_elaborato += f"## {topic}\n"
        # Unisce i paragrafi dei vari blocchi separandoli con un doppio a capo
        testo_elaborato += "\n\n".join(contenuti) + "\n\n"

    # 7. Salvataggio del Report del giorno
    data_oggi = datetime.datetime.now().strftime("%Y-%m-%d")
    nome_report = f"{data_oggi}_Rassegna_Stampa.md"

    # Crea la cartella Rassegne se non esiste (ulteriore sicurezza per Python)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Definiamo il percorso finale dentro la cartella Rassegne
    percorso_report = os.path.join(output_folder, nome_report)

    # Salviamo il file nel nuovo percorso
    with open(percorso_report, "w", encoding="utf-8") as f:
        f.write(f"# Rassegna Stampa {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n")
        f.write(testo_elaborato)

    print(f"{GREEN}Rassegna salvata in {percorso_report}{RESET}")
    
    # Apre automaticamente il report dalla cartella Rassegne
    os.system(f"start {percorso_report}")

if __name__ == "__main__":
    main()