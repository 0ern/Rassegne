import os
import datetime
import time
import feedparser
import ollama
import re

nome_modello = "llama3.1:8b" # (Llama 3.2 , Gemma 4)

def main():
    # 1. Controllo se il file delle fonti esiste
    if not os.path.exists("Fonti.txt"):
        print("Errore: Il file Fonti.txt non esiste. Crealo e inserisci i feed RSS.")
        return

    with open("Fonti.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("Nessun link trovato in Fonti.txt.")
        return

    print(f"Lettura di {len(urls)} fonti in corso...")

    # 2. Impostiamo il filtro temporale (Ultime 24 ore)
    ora_attuale = datetime.datetime.now(datetime.timezone.utc)
    ventiquattro_ore_fa = ora_attuale - datetime.timedelta(hours=24)
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
            print(f"Impossibile leggere la fonte {url}: {e}")
            
    if not notizie_raccolte:
        print("Non ci sono notizie pubblicate nelle ultime 24 ore nei tuoi feed.")
        return

    print(f"Trovate {len(notizie_raccolte)} notizie.\nConnessione a Ollama modello {nome_modello}")

    # 4. Gestione del Modello IA
    try:
        ollama.show(nome_modello)
    except Exception:
        print(f"Modello '{nome_modello}' non trovato. Download in corso (solo per la prima volta, attendere)...")
        try:
            ollama.pull(nome_modello)
        except Exception:
            print("Errore: Ollama non risponde. Assicurati che l'app Ollama sia aperta sul PC!")
            return

    # 5. Caricamento del prompt esterno e preparazione dei dati
    if not os.path.exists("Prompt_IA.txt"):
        print("Errore: Il file Prompt_IA.txt non esiste nella cartella.")
        return

    with open("Prompt_IA.txt", "r", encoding="utf-8") as f:
        prompt_base = f.read()

    # --- CONFIGURAZIONE ELABORAZIONE A BLOCCHI (BATCHING) ---
    dimensione_batch = 5  # Elabora massimo 5 notizie alla volta per garantire precisione assoluta
    totale_notizie = len(notizie_raccolte)
    
    # Questo dizionario conterrà tutti i riassunti divisi per topic
    # Struttura: {"Economia": ["testo blocco 1", "testo blocco 2"], "Lavoro": [...]}
    rassegna_per_topic = {}    
    print(f"Elaborazione...")

    # 6. Fase di Analisi (Map): l'IA elabora i piccoli gruppi
    for i in range(0, totale_notizie, dimensione_batch):
        batch_corrente = notizie_raccolte[i:i+dimensione_batch]
        numero_blocco = (i // dimensione_batch) + 1
        totale_blocchi = -(-totale_notizie // dimensione_batch)
        
        # print(f"-> Analisi blocco {numero_blocco} di {totale_blocchi}...")
        
        testo_per_ia = ""
        for idx_relativo, notizia in enumerate(batch_corrente):
            idx_assoluto = i + idx_relativo
            testo_per_ia += f"TAG_DA_COPIARE: [Link:{idx_assoluto}]\nTitolo: {notizia['title']}\nDescrizione: {notizia['summary']}\n\n"
            
        prompt = f"{prompt_base}\n\nEcco le notizie da elaborare:\n{testo_per_ia}"
        
        try:
            response = ollama.chat(
                model='llama3.1:8b',
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
            print(f"[ERRORE] Salto il blocco {numero_blocco} per un problema tecnico: {e}")
    
    testo_elaborato = ""    
    for topic, contenuti in rassegna_per_topic.items():
        testo_elaborato += f"## {topic}\n"
        # Unisce i paragrafi dei vari blocchi separandoli con un doppio a capo
        testo_elaborato += "\n\n".join(contenuti) + "\n\n"

    # 7. Salvataggio del Report del giorno
    data_oggi = datetime.datetime.now().strftime("%Y-%m-%d")
    nome_report = f"{data_oggi}_Rassegna_Stampa.md"

    # Crea la cartella Rassegne se non esiste (ulteriore sicurezza per Python)
    if not os.path.exists("Rassegne"):
        os.makedirs("Rassegne")

    # Definiamo il percorso finale dentro la cartella Rassegne
    percorso_report = os.path.join("Rassegne", nome_report)

    # Salviamo il file nel nuovo percorso
    with open(percorso_report, "w", encoding="utf-8") as f:
        f.write(f"# Rassegna Stampa {datetime.datetime.now().strftime('%d/%m/%Y')}\n\n")
        f.write(testo_elaborato)

    print(f"Rassegna salvata in {percorso_report}")
    
    # Apre automaticamente il report dalla cartella Rassegne
    os.system(f"start {percorso_report}")

if __name__ == "__main__":
    main()