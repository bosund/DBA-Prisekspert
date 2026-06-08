import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import sys
import os

class DBAScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DBA Scraper")
        self.root.geometry("600x500")
        
        # Frame for inputs
        input_frame = ttk.LabelFrame(root, text="Indstillinger", padding=(10, 10))
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Søgestreng
        ttk.Label(input_frame, text="Søgestreng (Fritekst):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.query_var = tk.StringVar(value="fender stratocaster")
        ttk.Entry(input_frame, textvariable=self.query_var, width=50).grid(row=0, column=1, sticky=tk.W, pady=2)

        # URL
        ttk.Label(input_frame, text="ELLER direkte URL:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.url_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.url_var, width=50).grid(row=1, column=1, sticky=tk.W, pady=2)

        # Sider
        ttk.Label(input_frame, text="Maks antal sider:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pages_var = tk.IntVar(value=5)
        ttk.Spinbox(input_frame, from_=1, to=1000, textvariable=self.pages_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)

        # Output fil
        ttk.Label(input_frame, text="Output filnavn:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.output_var = tk.StringVar(value="dba_oversigt.md")
        ttk.Entry(input_frame, textvariable=self.output_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=2)

        # Start Button
        self.start_btn = ttk.Button(root, text="Start Scraping", command=self.start_scraping)
        self.start_btn.pack(pady=5)

        # Output Text
        ttk.Label(root, text="Log:").pack(anchor=tk.W, padx=10)
        self.log_text = scrolledtext.ScrolledText(root, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_scraping(self):
        query = self.query_var.get().strip()
        url = self.url_var.get().strip()
        pages = self.pages_var.get()
        output = self.output_var.get().strip()

        if not query and not url:
            messagebox.showwarning("Fejl", "Du skal angive enten en søgestreng eller en URL.")
            return

        self.start_btn.config(state=tk.DISABLED)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Run in a background thread to prevent GUI freezing
        thread = threading.Thread(target=self.run_script, args=(query, url, pages, output))
        thread.daemon = True
        thread.start()

    def run_script(self, query, url, pages, output):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape_all.py")
        cmd = [sys.executable, script_path]
        
        if url:
            cmd.extend(["--url", url])
        elif query:
            cmd.extend(["--query", query])
            
        cmd.extend(["--pages", str(pages)])
        
        if output:
            cmd.extend(["--output", output])

        self.log(f"Kører: {' '.join(cmd)}")
        
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            # Popen to read output line by line
            script_dir = os.path.dirname(os.path.abspath(__file__))
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                cwd=script_dir,
                env=env
            )
            
            for line in process.stdout:
                self.root.after(0, self.log, line.strip())
                
            process.wait()
            
            if process.returncode == 0:
                self.root.after(0, self.log, "\n--- SUCCES: Scraping er færdig! ---")
            else:
                self.root.after(0, self.log, f"\n--- FEJL: Processen afsluttede med kode {process.returncode} ---")
                
        except Exception as e:
            self.root.after(0, self.log, f"\n--- EXCEPTION: {str(e)} ---")
            
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = DBAScraperGUI(root)
    root.mainloop()
