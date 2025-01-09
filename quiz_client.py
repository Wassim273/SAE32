import tkinter as tk
from tkinter import messagebox, ttk
import socket
import json
import random
import time

class QuizClient:
    def __init__(self, host='localhost', port=12345):
        """Initialisation de la connexion au serveur"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Tentative de connexion au serveur {host}:{port}")
            self.socket.connect((host, port))
            print("Connexion réussie au serveur")
        except ConnectionRefusedError:
            messagebox.showerror(
                "Erreur de connexion",
                "Impossible de se connecter au serveur.\nVérifiez que le serveur est démarré."
            )
            raise
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la connexion: {str(e)}")
            raise
        
        self.socket.settimeout(10.0)  # Timeout de 10 secondes
        self.user_id = None
        self.current_game_id = None

    def send_command(self, command_type, data=None):
        """Envoie une commande au serveur"""
        if data is None:
            data = {}
            
        command = {
            'type': command_type,
            'data': data
        }
        
        try:
            print(f"Envoi de la commande: {command_type}")
            self.socket.send(json.dumps(command).encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            print(f"Réponse reçue: {response}")
            return json.loads(response)
        except socket.timeout:
            print("Timeout de la connexion")
            return {'status': 'error', 'message': 'Le serveur ne répond pas'}
        except Exception as e:
            print(f"Erreur lors de l'envoi/réception: {e}")
            return {'status': 'error', 'message': str(e)}

    def login(self, username, password):
        """Connexion au serveur"""
        return self.send_command('login', {
            'username': username,
            'password': password
        })

    def register(self, username, password):
        """Inscription sur le serveur"""
        return self.send_command('register', {
            'username': username,
            'password': password
        })

    def get_themes(self):
        """Récupère la liste des thèmes"""
        return self.send_command('get_themes')

    def start_game(self, theme_id):
        """Démarre une nouvelle partie"""
        self.current_game_id = None  # Réinitialise l'ID de partie
        self.current_theme_id = theme_id  # Stocke le thème actuel
        return self.send_command('start_game', {
            'theme_id': theme_id,
            'user_id': self.user_id
        })

    def submit_answer(self, answer_data):
        """Envoie une réponse au serveur"""
        # Ajoute l'ID de partie et le thème à la requête
        request_data = {
            'game_id': self.current_game_id,
            'answer': answer_data.get('answer') if isinstance(answer_data, dict) else answer_data,
            'time_taken': answer_data.get('time_taken', 30) if isinstance(answer_data, dict) else 30
        }
        
        # Ajoute le theme_id si disponible (important pour le mode duel)
        if hasattr(self, 'current_theme_id'):
            request_data['theme_id'] = self.current_theme_id
            
        return self.send_command('submit_answer', request_data)

    def get_game_summary(self):
        """Récupère le résumé de la partie"""
        return self.send_command('get_game_summary', {
            'game_id': self.current_game_id
        })

    def close(self):
        """Ferme la connexion"""
        try:
            self.socket.close()
        except:
            pass
        
    def get_leaderboard(self, theme_id=None):
        """Récupère le classement"""
        return self.send_command('get_leaderboard', {
            'theme_id': theme_id
        })
    def create_duel_room(self, theme_id):
        """Crée un salon de duel"""
        return self.send_command('create_duel_room', {
            'theme_id': theme_id,
            'user_id': self.user_id
        })

    def join_duel_room(self, room_code):
        """Rejoint un salon de duel"""
        return self.send_command('join_duel_room', {
            'room_code': room_code,
            'user_id': self.user_id
        })
    def get_room_players(self, room_code):
        """Récupère la liste des joueurs dans un salon"""
        return self.send_command('get_room_players', {
            'room_code': room_code,
            'user_id': self.user_id
        })

    def start_duel(self, room_code):
        """Démarre une partie en mode duel"""
        return self.send_command('start_duel', {
            'room_code': room_code,
            'user_id': self.user_id
        })   
class QuizGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Quiz Game - Client")
        self.root.geometry("800x600")
        
        try:
            self.client = QuizClient()
        except Exception:
            self.root.destroy()
            return
            
        self.main_frame = tk.Frame(root, padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')
        
        self.score = 0
        self.start_time = None
        self.answer_time = None
        
        self.show_login_screen()
    def clear_frame(self):
        """Nettoie l'écran"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_theme_selection(self):
        """Affiche la sélection des thèmes"""
        self.clear_frame()
        
        # En-tête avec titre et classement
        header_frame = tk.Frame(self.main_frame)
        header_frame.pack(fill='x', pady=20)
        
        tk.Label(
            header_frame,
            text="Quiz Game",
            font=('Arial', 24, 'bold')
        ).pack(side=tk.LEFT, padx=20)
        
        tk.Button(
            header_frame,
            text="Voir les classements",
            command=self.show_leaderboard,
            font=('Arial', 12)
        ).pack(side=tk.RIGHT, padx=20)
        tk.Button(
            header_frame,
            text="Mode Duel",
            command=self.show_duel_menu,
            font=('Arial', 12),
            bg='#2196F3',  # Bleu pour différencier
            fg='white'
        ).pack(side=tk.RIGHT, padx=20)

        # Message de bienvenue
        tk.Label(
            self.main_frame,
            text="Choisissez un thème pour commencer",
            font=('Arial', 14)
        ).pack(pady=(0, 20))

        # Cadre pour les thèmes
        themes_frame = tk.Frame(self.main_frame)
        themes_frame.pack(fill='x', padx=50)
        
        response = self.client.get_themes()
        if response['status'] == 'success':
            for theme_id, theme_name in response['themes']:
                tk.Button(
                    themes_frame,
                    text=theme_name,
                    command=lambda t=theme_id: self.handle_theme_selection(t),
                    font=('Arial', 12),
                    width=30,
                    bg='#f0f0f0',
                    relief=tk.RAISED,
                    bd=2
                ).pack(pady=5)
        else:
            messagebox.showerror("Erreur", "Impossible de récupérer les thèmes")

    def show_login_screen(self):
        """Affiche l'écran de connexion"""
        self.clear_frame()
        
        # Titre
        tk.Label(
            self.main_frame,
            text="Quiz Game",
            font=('Arial', 24, 'bold')
        ).pack(pady=20)
        
        # Frame de connexion
        login_frame = tk.Frame(self.main_frame)
        login_frame.pack(pady=20)
        
        tk.Label(
            login_frame,
            text="Nom d'utilisateur:",
            font=('Arial', 12)
        ).grid(row=0, column=0, pady=5, padx=5, sticky='e')
        
        self.username_entry = tk.Entry(login_frame, font=('Arial', 12))
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)
        
        tk.Label(
            login_frame,
            text="Mot de passe:",
            font=('Arial', 12)
        ).grid(row=1, column=0, pady=5, padx=5, sticky='e')
        
        self.password_entry = tk.Entry(login_frame, show="*", font=('Arial', 12))
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Frame pour les boutons
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Se connecter",
            command=self.handle_login,
            font=('Arial', 12),
            width=15,
            bg='#4CAF50',
            fg='white'
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            button_frame,
            text="S'inscrire",
            command=self.handle_register,
            font=('Arial', 12),
            width=15
        ).pack(side=tk.LEFT, padx=10)

        # Bind Enter key to login
        self.password_entry.bind('<Return>', lambda e: self.handle_login())

    def handle_login(self):
        """Gère la connexion"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
            return
            
        response = self.client.login(username, password)
        if response['status'] == 'success':
            self.client.user_id = response['user_id']
            self.show_theme_selection()
        else:
            messagebox.showerror("Erreur", response.get('message', "Erreur de connexion"))
    def handle_register(self):
        """Gère l'inscription"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
            return
            
        if len(username) < 3 or len(password) < 3:
            messagebox.showerror(
                "Erreur",
                "Le nom d'utilisateur et le mot de passe doivent faire au moins 3 caractères"
            )
            return
            
        response = self.client.register(username, password)
        if response['status'] == 'success':
            messagebox.showinfo("Succès", "Compte créé avec succès!")
            self.handle_login()
        else:
            messagebox.showerror("Erreur", response.get('message', "Erreur d'inscription"))

    def handle_theme_selection(self, theme_id):
        """Gère la sélection d'un thème"""
        try:
            response = self.client.start_game(theme_id)
            if response['status'] == 'success':
                self.client.current_game_id = response['game_id']
                self.start_time = time.time()
                self.score = 0
                self.show_question(response['question'])
            else:
                messagebox.showerror(
                    "Erreur",
                    response.get('message', "Impossible de démarrer la partie")
                )
                self.show_theme_selection()
        except Exception as e:
            print(f"Erreur lors de la sélection du thème: {e}")
            messagebox.showerror(
                "Erreur",
                "Une erreur est survenue. Retour au menu principal."
            )
            self.show_theme_selection()

    def show_question(self, question):
        """Affiche une question avec chronomètre"""
        self.clear_frame()
        self.answer_time = time.time()
        
        # Top frame pour timer et score
        top_frame = tk.Frame(self.main_frame)
        top_frame.pack(fill='x', pady=10)
        
        # Timer frame (gauche)
        timer_frame = tk.Frame(top_frame)
        timer_frame.pack(side=tk.LEFT)
        
        self.time_left = 30
        self.timer_label = tk.Label(
            timer_frame,
            text=f"Temps: {self.time_left}s",
            font=('Arial', 14, 'bold')
        )
        self.timer_label.pack(side=tk.LEFT, padx=10)
        
        # Score (droite)
        tk.Label(
            top_frame,
            text=f"Score: {self.score}",
            font=('Arial', 14, 'bold')
        ).pack(side=tk.RIGHT, padx=10)
        
        # Question
        question_frame = tk.Frame(self.main_frame)
        question_frame.pack(fill='x', pady=20)
        
        tk.Label(
            question_frame,
            text=question[4],
            font=('Arial', 16, 'bold'),
            wraplength=600,
            justify='center'
        ).pack()
        
        # Frame pour les réponses
        answers_frame = tk.Frame(self.main_frame)
        answers_frame.pack(pady=20)
        
        # Gestion différente selon le type de question
        question_type = question[2]
        
        if question_type == 5:  # Question ouverte
            answer_entry_frame = tk.Frame(answers_frame)
            answer_entry_frame.pack()
            
            self.answer_entry = tk.Entry(
                answer_entry_frame,
                font=('Arial', 14)
            )
            self.answer_entry.pack(side=tk.LEFT, padx=5)
            self.answer_entry.focus()
            
            tk.Button(
                answer_entry_frame,
                text="Valider",
                command=lambda: self.handle_answer(self.answer_entry.get()),
                font=('Arial', 12),
                bg='#4CAF50',
                fg='white'
            ).pack(side=tk.LEFT)
            
            # Bind Enter key
            self.answer_entry.bind('<Return>', lambda e: self.handle_answer(self.answer_entry.get()))
            
        else:
            # Questions à choix
            answers = [question[5]]  # Bonne réponse
            if question[6]: answers.append(question[6])
            if question[7]: answers.append(question[7])
            if question[8]: answers.append(question[8])
            
            random.shuffle(answers)
            
            for answer in answers:
                if answer:
                    tk.Button(
                        answers_frame,
                        text=answer,
                        command=lambda a=answer: self.handle_answer(a),
                        font=('Arial', 12),
                        width=40,
                        height=2
                    ).pack(pady=5)
        
        # Bouton pour passer
        tk.Button(
            self.main_frame,
            text="Passer",
            command=lambda: self.handle_answer(None),
            font=('Arial', 12)
        ).pack(side=tk.BOTTOM, pady=20)
        
        # Démarrer le timer
        self.update_timer()      

    def update_timer(self):
        """Met à jour le chronomètre"""
        if hasattr(self, 'time_left') and self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=f"Temps: {self.time_left}s")
            # Change la couleur selon le temps restant
            if self.time_left <= 5:
                self.timer_label.config(fg='red')
            elif self.time_left <= 10:
                self.timer_label.config(fg='orange')
            # Actualise chaque seconde
            self.root.after(1000, self.update_timer)
        else:
            # Temps écoulé
            self.handle_answer(None)

    def handle_answer(self, answer):
        """Gère la réponse à une question"""
        if not hasattr(self, 'time_left'):  # Évite les doubles soumissions
            return
            
        time_taken = 30 - self.time_left  # Temps pris pour répondre
        del self.time_left  # Empêche les soumissions multiples
        
        try:
            response = self.client.submit_answer({
                'answer': answer,
                'time_taken': time_taken
            })
            
            if response['status'] == 'success':
                if answer is None:
                    messagebox.showinfo("Info", "Question passée")
                elif response['is_correct']:
                    self.score += response['points']
                    messagebox.showinfo(
                        "Correct!",
                        f"+{response['points']} points\nTemps: {time_taken}s"
                    )
                else:
                    messagebox.showinfo(
                        "Incorrect",
                        f"La bonne réponse était: {response['correct_answer']}\nTemps: {time_taken}s"
                    )
                
                if response['game_finished']:
                    self.show_game_summary()
                else:
                    self.show_question(response['next_question'])
            else:
                messagebox.showerror("Erreur", "Erreur lors de l'envoi de la réponse")
                self.show_theme_selection()
        except Exception as e:
            print(f"Erreur lors du traitement de la réponse: {e}")
            messagebox.showerror(
                "Erreur",
                "Une erreur est survenue. Retour à la sélection des thèmes."
            )
            self.show_theme_selection()

    def show_game_summary(self):
        """Affiche le résumé de la partie"""
        try:
            response = self.client.get_game_summary()
            if response['status'] != 'success':
                messagebox.showerror("Erreur", "Impossible de récupérer le résumé")
                self.show_theme_selection()
                return

            self.clear_frame()
            
            # Titre
            tk.Label(
                self.main_frame,
                text="Récapitulatif de la partie",
                font=('Arial', 24, 'bold')
            ).pack(pady=20)
            
            # Score et temps
            stats_frame = tk.Frame(self.main_frame)
            stats_frame.pack(fill='x', pady=10)
            
            tk.Label(
                stats_frame,
                text=f"Score final: {response['score']}",
                font=('Arial', 16, 'bold')
            ).pack(pady=5)
            
            tk.Label(
                stats_frame,
                text=f"Temps total: {response['total_time']:.1f} secondes",
                font=('Arial', 16)
            ).pack(pady=5)
            # Frame scrollable pour l'historique
            container = tk.Frame(self.main_frame)
            container.pack(fill="both", expand=True, pady=10)
            
            canvas = tk.Canvas(container)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Historique des questions
            for i, qa in enumerate(response['history'], 1):
                question_frame = tk.Frame(
                    scrollable_frame,
                    relief="groove",
                    borderwidth=1
                )
                question_frame.pack(fill="x", pady=5, padx=5, ipadx=5, ipady=5)
                
                # Question
                tk.Label(
                    question_frame,
                    text=f"Question {i}: {qa['question']}",
                    font=('Arial', 12, 'bold'),
                    wraplength=600,
                    justify='left'
                ).pack(anchor="w")
                
                # Réponse de l'utilisateur
                tk.Label(
                    question_frame,
                    text=f"Votre réponse: {qa['user_answer'] if qa['user_answer'] else 'Passée'}",
                    font=('Arial', 12),
                    fg='green' if qa['is_correct'] else 'red'
                ).pack(anchor="w")
                
                # Bonne réponse si incorrect
                if not qa['is_correct']:
                    tk.Label(
                        question_frame,
                        text=f"Bonne réponse: {qa['correct_answer']}",
                        font=('Arial', 12)
                    ).pack(anchor="w")
                
                # Points et temps
                tk.Label(
                    question_frame,
                    text=f"Points: {qa['points'] if qa['is_correct'] else 0}/{qa['points']} - Temps: {qa['time_taken']:.1f}s",
                    font=('Arial', 12)
                ).pack(anchor="w")
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Boutons de fin
            button_frame = tk.Frame(self.main_frame)
            button_frame.pack(pady=20)
            
            tk.Button(
                button_frame,
                text="Nouvelle partie",
                command=self.show_theme_selection,
                font=('Arial', 12),
                bg='#4CAF50',
                fg='white'
            ).pack(side=tk.LEFT, padx=10)
            
            tk.Button(
                button_frame,
                text="Voir le classement",
                command=self.show_leaderboard,
                font=('Arial', 12)
            ).pack(side=tk.LEFT, padx=10)
            
        except Exception as e:
            print(f"Erreur lors de l'affichage du résumé: {e}")
            messagebox.showerror(
                "Erreur",
                "Une erreur est survenue lors de l'affichage du résumé"
            )
            self.show_theme_selection()

    def show_leaderboard(self, theme_id=None):
        """Affiche le classement"""
        self.clear_frame()
        
        # En-tête avec titre
        header_frame = tk.Frame(self.main_frame)
        header_frame.pack(fill='x', pady=20)
        
        tk.Label(
            header_frame,
            text="Classement",
            font=('Arial', 24, 'bold')
        ).pack(side=tk.LEFT, padx=20)

        # Boutons de filtres par thème
        filter_frame = tk.Frame(self.main_frame)
        filter_frame.pack(pady=10)
        
        tk.Button(
            filter_frame,
            text="Classement Général",
            command=lambda: self.show_leaderboard(None),
            font=('Arial', 11),
            bg='#4CAF50' if theme_id is None else '#f0f0f0',
            fg='white' if theme_id is None else 'black'
        ).pack(side=tk.LEFT, padx=5)

        # Boutons pour chaque thème
        themes_response = self.client.get_themes()
        if themes_response['status'] == 'success':
            for tid, theme_name in themes_response['themes']:
                tk.Button(
                    filter_frame,
                    text=theme_name,
                    command=lambda t=tid: self.show_leaderboard(t),
                    font=('Arial', 11),
                    bg='#4CAF50' if theme_id == tid else '#f0f0f0',
                    fg='white' if theme_id == tid else 'black'
                ).pack(side=tk.LEFT, padx=5)

        # Tableau des scores
        scores_frame = tk.Frame(self.main_frame)
        scores_frame.pack(pady=20, padx=20)
        
        # En-têtes
        columns = ["Position", "Joueur", "Score", "Temps"]
            
        for col, header in enumerate(columns):
            tk.Label(
                scores_frame,
                text=header,
                font=('Arial', 12, 'bold')
            ).grid(row=0, column=col, padx=10, sticky='w')
        
        # Récupération des scores
        response = self.client.get_leaderboard(theme_id)
        if response['status'] == 'success':
            scores = response.get('scores', [])
            
            if not scores:
                tk.Label(
                    scores_frame,
                    text="Aucun score enregistré",
                    font=('Arial', 12),
                    fg='gray'
                ).grid(row=1, column=0, columnspan=len(columns), pady=20)
            else:
                for i, score in enumerate(scores, 1):
                    # Position
                    tk.Label(
                        scores_frame,
                        text=str(i),
                        font=('Arial', 12)
                    ).grid(row=i, column=0, padx=10, pady=5, sticky='w')
                    
                    # Username
                    tk.Label(
                        scores_frame,
                        text=str(score[0]),  # username
                        font=('Arial', 12)
                    ).grid(row=i, column=1, padx=10, pady=5, sticky='w')
                    
                    # Score (index 2 pour les scores par thème, index 2 pour le classement général)
                    tk.Label(
                        scores_frame,
                        text=str(score[1] if theme_id is not None else score[2]),  # score
                        font=('Arial', 12)
                    ).grid(row=i, column=2, padx=10, pady=5, sticky='w')
                    
                    # Temps (index 2 pour les scores par thème, index 3 pour le classement général)
                    tk.Label(
                        scores_frame,
                        text=f"{score[2] if theme_id is not None else score[3]:.1f}s",  # temps
                        font=('Arial', 12)
                    ).grid(row=i, column=3, padx=10, pady=5, sticky='w')
        else:
            tk.Label(
                scores_frame,
                text="Impossible de récupérer les scores",
                font=('Arial', 12),
                fg='red'
            ).grid(row=1, column=0, columnspan=len(columns), pady=20)
        
        # Bouton retour
        tk.Button(
            self.main_frame,
            text="Retour",
            command=self.show_theme_selection,
            font=('Arial', 14),
            width=20
        ).pack(pady=20)
    def show_duel_menu(self):
        """Affiche le menu des duels"""
        self.clear_frame()
        
        # Titre
        tk.Label(
            self.main_frame,
            text="Mode Duel",
            font=('Arial', 24, 'bold')
        ).pack(pady=20)
        
        # Boutons pour créer ou rejoindre
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(pady=30)
        
        tk.Button(
            button_frame,
            text="Créer un salon",
            command=self.show_create_duel_room,
            font=('Arial', 14),
            width=20,
            bg='#4CAF50',
            fg='white'
        ).pack(pady=10)
        
        tk.Button(
            button_frame,
            text="Rejoindre un salon",
            command=self.show_join_duel_room,
            font=('Arial', 14),
            width=20
        ).pack(pady=10)
        
        # Bouton retour
        tk.Button(
            self.main_frame,
            text="Retour",
            command=self.show_theme_selection,
            font=('Arial', 12)
        ).pack(pady=20)

    def show_create_duel_room(self):
        """Affiche l'écran de création de salon"""
        self.clear_frame()
        
        tk.Label(
            self.main_frame,
            text="Créer un salon de duel",
            font=('Arial', 24, 'bold')
        ).pack(pady=20)
        
        # Sélection du thème
        themes_frame = tk.Frame(self.main_frame)
        themes_frame.pack(pady=20)
        
        tk.Label(
            themes_frame,
            text="Choisissez un thème :",
            font=('Arial', 14)
        ).pack(pady=10)
        
        response = self.client.get_themes()
        if response['status'] == 'success':
            for theme_id, theme_name in response['themes']:
                tk.Button(
                    themes_frame,
                    text=theme_name,
                    command=lambda t=theme_id: self.create_duel_room(t),
                    font=('Arial', 12),
                    width=30
                ).pack(pady=5)
        
        # Bouton retour
        tk.Button(
            self.main_frame,
            text="Retour",
            command=self.show_duel_menu,
            font=('Arial', 12)
        ).pack(pady=20)

    def show_join_duel_room(self):
        """Affiche l'écran pour rejoindre un salon"""
        self.clear_frame()
        
        tk.Label(
            self.main_frame,
            text="Rejoindre un salon",
            font=('Arial', 24, 'bold')
        ).pack(pady=20)
        
        # Entrée du code
        entry_frame = tk.Frame(self.main_frame)
        entry_frame.pack(pady=30)
        
        tk.Label(
            entry_frame,
            text="Code du salon :",
            font=('Arial', 14)
        ).pack()
        
        code_entry = tk.Entry(entry_frame, font=('Arial', 16), width=10)
        code_entry.pack(pady=10)
        
        tk.Button(
            entry_frame,
            text="Rejoindre",
            command=lambda: self.join_duel_room(code_entry.get()),
            font=('Arial', 12),
            bg='#4CAF50',
            fg='white'
        ).pack(pady=10)
        
        # Bouton retour
        tk.Button(
            self.main_frame,
            text="Retour",
            command=self.show_duel_menu,
            font=('Arial', 12)
        ).pack(pady=20)

    def create_duel_room(self, theme_id):
        """Crée un salon de duel"""
        response = self.client.create_duel_room(theme_id)
        if response['status'] == 'success':
            code = response['room_code']
            messagebox.showinfo(
                "Salon créé",
                f"Votre code de salon est : {code}\n" +
                "Partagez ce code avec vos amis pour qu'ils puissent vous rejoindre!"
            )
            self.show_duel_waiting_room(code)
        else:
            messagebox.showerror("Erreur", "Impossible de créer le salon")
            self.show_duel_menu()

    def join_duel_room(self, room_code):
        """Rejoint un salon de duel"""
        if not room_code:
            messagebox.showerror("Erreur", "Veuillez entrer un code")
            return
            
        response = self.client.join_duel_room(room_code)
        if response['status'] == 'success':
            self.show_duel_waiting_room(room_code)
        else:
            messagebox.showerror(
                "Erreur",
                response.get('message', "Impossible de rejoindre le salon")
            )

    def show_duel_waiting_room(self, room_code):
        """Affiche la salle d'attente du duel"""
        self.clear_frame()
        
        tk.Label(
            self.main_frame,
            text=f"Salon de duel - Code : {room_code}",
            font=('Arial', 24, 'bold')
        ).pack(pady=20)
        
        # Liste des joueurs
        tk.Label(
            self.main_frame,
            text="Joueurs présents :",
            font=('Arial', 16)
        ).pack(pady=10)
        
        # Frame pour la liste des joueurs
        self.players_frame = tk.Frame(self.main_frame)
        self.players_frame.pack(pady=20)
        
        # Bouton pour démarrer (visible uniquement pour l'hôte)
        self.start_button = tk.Button(
            self.main_frame,
            text="Démarrer la partie",
            command=lambda: self.start_duel(room_code),
            font=('Arial', 14),
            bg='#4CAF50',
            fg='white',
            state='disabled'  # Désactivé par défaut
        )
        self.start_button.pack(pady=10)
        
        # Bouton quitter
        tk.Button(
            self.main_frame,
            text="Quitter le salon",
            command=self.show_duel_menu,
            font=('Arial', 12)
        ).pack(pady=20)
        
        # Met à jour la liste des joueurs
        self.update_player_list(room_code)
        
        # Rafraîchissement périodique
        self.refresh_task = self.root.after(1000, lambda: self.update_player_list(room_code))

    def update_player_list(self, room_code):
        """Met à jour la liste des joueurs"""
        response = self.client.get_room_players(room_code)
        if response['status'] == 'success':
            # Vérifie si la partie a démarré
            if response.get('game_started'):
                # Si la partie a démarré, initialise la partie pour ce joueur
                self.client.current_game_id = response.get('game_id')
                self.client.current_theme_id = response.get('theme_id')  # Ajout de cette ligne
                if 'first_question' in response:
                    self.show_question(response['first_question'])
                return  # Arrête la mise à jour périodique car la partie a commencé
            
            # Si la partie n'a pas démarré, continue la mise à jour normale
            for widget in self.players_frame.winfo_children():
                widget.destroy()
            
            for player in response.get('players', []):
                label_text = f"{player['username']}"
                if player['is_host']:
                    label_text += " (Hôte)"
                    
                tk.Label(
                    self.players_frame,
                    text=label_text,
                    font=('Arial', 14),
                    fg='#4CAF50' if player['is_host'] else 'black'
                ).pack(pady=5)
            
            players_count = len(response.get('players', []))
            if response.get('is_host'):
                if self.start_button:
                    if players_count >= 2:
                        self.start_button.config(state='normal')
                    else:
                        self.start_button.config(state='disabled')
            elif hasattr(self, 'start_button'):
                self.start_button.pack_forget()
            
            if hasattr(self, 'refresh_task'):
                self.root.after_cancel(self.refresh_task)
            self.refresh_task = self.root.after(1000, lambda: self.update_player_list(room_code))

    def start_duel(self, room_code):
        """Démarre la partie en mode duel"""
        response = self.client.start_duel(room_code)
        if response['status'] == 'success':
            messagebox.showinfo("Succès", "La partie va commencer !")
            self.client.current_game_id = response.get('game_id')
            # Démarre la partie avec la première question
            if 'first_question' in response:
                self.show_question(response['first_question'])
        else:
            messagebox.showerror("Erreur", response.get('message', "Impossible de démarrer la partie"))    
def main():
    root = tk.Tk()
    app = QuizGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()  