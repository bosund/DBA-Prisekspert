"""
DISCLAIMER:
Dette program er udelukkende udviklet til uddannelsesmæssige (educational) formål 
og som et personligt projekt. Det er op til brugeren af programmet at overholde gældende 
lovgivning samt handelsbetingelser (Terms of Service) for de hjemmesider, der interageres med. 
Forfatteren tager intet ansvar for misbrug eller blokeringer forårsaget af dette værktøj.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import sys
import os

import scrape_all

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

        # Action Buttons Frame
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start Scraping", command=self.start_scraping)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop / Annuller", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_event = threading.Event()

        # Output Text
        ttk.Label(root, text="Log:").pack(anchor=tk.W, padx=10)
        self.log_text = scrolledtext.ScrolledText(root, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def stop_scraping(self):
        self.stop_event.set()
        self.stop_btn.config(state=tk.DISABLED)
        self.log("\n--- Annullerer scraping... Venter på baggrundsopgaver ---")

    def start_scraping(self):
        query = self.query_var.get().strip()
        url = self.url_var.get().strip()
        pages = self.pages_var.get()

        if not query and not url:
            messagebox.showwarning("Fejl", "Du skal angive enten en søgestreng eller en URL.")
            return

        self.stop_event.clear()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Run in a background thread to prevent GUI freezing
        thread = threading.Thread(target=self.run_script, args=(query, url, pages))
        thread.daemon = True
        thread.start()

    def run_script(self, query, url, pages):
        def gui_logger(msg):
            self.root.after(0, self.log, msg)

        try:
            results = scrape_all.get_all_ads(query, url, pages, log_func=gui_logger, stop_event=self.stop_event)
            if not results:
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
                return

            categories = list(set(r['category_path'] for r in results))
            categories.sort()

            # Trigger the filter popup on the main thread
            self.root.after(0, self.show_category_filter, results, categories, query, url, pages)
            
        except Exception as e:
            gui_logger(f"\n--- EXCEPTION: {str(e)} ---")
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def show_category_filter(self, results, categories, query, url, pages):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        popup = tk.Toplevel(self.root)
        popup.title("Vælg Kategorier")
        popup.geometry("500x400")
        popup.transient(self.root)
        popup.grab_set()

        ttk.Label(popup, text="Vælg hvilke kategorier du vil inkludere i oversigten:").pack(pady=10, padx=10, anchor=tk.W)

        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Scrolled frame logic for categories (using Canvas)
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checkbox_vars = {}
        for cat in categories:
            var = tk.BooleanVar(value=True)
            checkbox_vars[cat] = var
            cb = ttk.Checkbutton(scrollable_frame, text=cat, variable=var)
            cb.pack(anchor=tk.W, pady=2)

        def save_file(format_type):
            selected_cats = {cat for cat, var in checkbox_vars.items() if var.get()}
            filtered_results = [r for r in results if r['category_path'] in selected_cats]
            
            title = url if url else query.title()
            
            if format_type == 'excel':
                file_types = [("Excel filer", "*.xlsx"), ("Alle filer", "*.*")]
                default_ext = ".xlsx"
            else:
                file_types = [("Markdown filer", "*.md"), ("Alle filer", "*.*")]
                default_ext = ".md"
                
            output_path = filedialog.asksaveasfilename(
                parent=popup,
                title="Gem annonceoversigt",
                defaultextension=default_ext,
                filetypes=file_types
            )
            
            if not output_path:
                return # Brugeren afbrød gem

            try:
                if format_type == 'excel':
                    scrape_all.write_excel(filtered_results, output_path, title, pages)
                else:
                    scrape_all.write_markdown(filtered_results, output_path, title, pages)
                self.log(f"\n--- SUCCES: Scraping færdig. Gemt {len(filtered_results)} annoncer i {os.path.basename(output_path)} ---")
                popup.destroy()
                
                # Vis succes-besked
                success_dlg = tk.Toplevel(self.root)
                success_dlg.title("Fil gemt")
                success_dlg.geometry("450x150")
                success_dlg.transient(self.root)
                success_dlg.grab_set()
                
                ttk.Label(success_dlg, text="Filen blev gemt med succes!", font=("TkDefaultFont", 10, "bold")).pack(pady=(15, 5))
                
                # Gør stien pæn for visning
                display_path = os.path.normpath(output_path)
                ttk.Label(success_dlg, text=f"Sti: {display_path}", wraplength=430).pack(pady=5, padx=10)
                
                btn_frame2 = ttk.Frame(success_dlg)
                btn_frame2.pack(pady=10)
                
                def open_file_and_close():
                    try:
                        os.startfile(output_path)
                    except Exception as ex:
                        messagebox.showerror("Fejl", f"Kunne ikke åbne filen: {str(ex)}")
                    success_dlg.destroy()
                
                ttk.Button(btn_frame2, text="Åbn fil", command=open_file_and_close).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame2, text="OK", command=success_dlg.destroy).pack(side=tk.LEFT, padx=5)

            except Exception as e:
                self.log(f"\n--- FEJL under gem: {str(e)} ---")
                messagebox.showerror("Fejl under gem", f"Der opstod en fejl under forsøget på at gemme filen:\n\n{str(e)}")

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Gem som Excel", command=lambda: save_file('excel')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Gem som Markdown", command=lambda: save_file('md')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Luk uden at gemme", command=popup.destroy).pack(side=tk.LEFT, padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = DBAScraperGUI(root)
    root.mainloop()
