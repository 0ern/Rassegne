import os
import datetime
import time
import feedparser
import ollama

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

    print(f"Trovate {len(notizie_raccolte)} notizie recenti. Connessione a Ollama...")

    # 4. Gestione del Modello IA (Usiamo Llama 3.2: leggero, veloce e potente in locale)
    nome_modello = "llama3.2"
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

    testo_per_ia = ""
    for idx, notizia in enumerate(notizie_raccolte):
        testo_per_ia += f"ID:[{idx}] | Titolo: {notizia['title']} | Descrizione: {notizia['summary']}\n\n"

    # Uniamo le istruzioni del prompt alle notizie reali in modo automatico e sicuro
        prompt = f"{prompt_base}\n\nEcco le notizie da elaborare:\n{testo_per_ia}"

    print("L'IA sta analizzando e raggruppando le notizie per topic...")
    try:
        risposta = ollama.chat(
            model=nome_modello, # modello che usi
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.2,  # Più basso è, più l'IA è obbediente e precisa con i link
                'num_ctx': 8192      # Estende la memoria per gestire molte notizie insieme
            }
        )
        testo_elaborato = risposta['message']['content']
    except Exception as e:
        print(f"Errore durante l'elaborazione dell'IA: {e}")
        return

    # 6. Sostituiamo i tag ID con i veri link cliccabili
    for idx, notizia in enumerate(notizie_raccolte):
        testo_elaborato = testo_elaborato.replace(f"[Link:{idx}]", f"([Leggi l'articolo originale]({notizia['link']}))")

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

    print(f"Rassegna completata con successo! Salvata in {percorso_report}")
    
    # Apre automaticamente il report dalla cartella Rassegne
    os.system(f"start {percorso_report}")

if __name__ == "__main__":
    main()