import socket
import threading
import json
from quiz_database import QuizDatabase, QuestionType
import time
import random
import unicodedata

# Fonction pour normaliser une chaîne (supprime les accents et met en minuscules)
def normalize_string(input_string):
    return unicodedata.normalize('NFD', input_string).encode('ascii', 'ignore').decode('utf-8').lower()

# Fonction pour vérifier si la réponse est correcte
def is_correct_answer(user_answer, correct_answer):
    return normalize_string(user_answer) == normalize_string(correct_answer)

class QuizServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Serveur démarré sur {host}:{port}")
            
        except Exception as e:
            print(f"Erreur lors du démarrage du serveur: {e}")
            raise
        
        self.db = QuizDatabase('quiz.db')
        self.clients = {}
        self.active_games = {}
        self.duel_rooms = {}

    def start(self):
        print("En attente de connexions...")
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"Nouvelle connexion de {address}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print("\nArrêt du serveur...")
                break
            except Exception as e:
                print(f"Erreur de connexion: {e}")

    def handle_client(self, client_socket, address):
        print(f"Gestion du client {address}")
        try:
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break

                print(f"Reçu de {address}: {data}")
                command = json.loads(data)
                response = self.process_command(command, client_socket)
                
                print(f"Envoi à {address}: {response}")
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"Erreur avec le client {address}: {e}")
        finally:
            if client_socket in self.clients:
                del self.clients[client_socket]
            client_socket.close()
            print(f"Connexion fermée avec {address}")

    def process_command(self, command, client_socket):
        cmd_type = command.get('type')
        data = command.get('data', {})
        
        try:
            if cmd_type == 'login':
                return self.handle_login(data)
            elif cmd_type == 'register':
                return self.handle_register(data)
            elif cmd_type == 'get_themes':
                return self.handle_get_themes()
            elif cmd_type == 'start_game':
                return self.handle_start_game(data, client_socket)
            elif cmd_type == 'submit_answer':
                return self.handle_submit_answer(data, client_socket)
            elif cmd_type == 'get_game_summary':
                return self.handle_get_game_summary(data)
            elif cmd_type == 'get_leaderboard':
                return self.handle_get_leaderboard(data)
            elif cmd_type == 'create_duel_room':
                return self.handle_create_duel_room(data)
            elif cmd_type == 'join_duel_room':
                return self.handle_join_duel_room(data)
            elif cmd_type == 'get_room_players':
                return self.handle_get_room_players(data)
            elif cmd_type == 'start_duel':
                return self.handle_start_duel(data)
            else:
                return {'status': 'error', 'message': 'Commande inconnue'}
        except Exception as e:
            print(f"Erreur lors du traitement de la commande: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_login(self, data):
        username = data.get('username')
        password = data.get('password')
        user_id = self.db.verify_user(username, password)
        if user_id:
            return {'status': 'success', 'user_id': user_id}
        return {'status': 'error', 'message': 'Identifiants invalides'}

    def handle_register(self, data):
        username = data.get('username')
        password = data.get('password')
        if self.db.add_user(username, password):
            return {'status': 'success'}
        return {'status': 'error', 'message': 'Nom d\'utilisateur déjà pris'}

    def handle_get_themes(self):
        themes = self.db.get_all_themes()
        return {'status': 'success', 'themes': themes}
    def handle_start_game(self, data, client_socket):
        """Démarre une nouvelle partie"""
        try:
            theme_id = data.get('theme_id')
            user_id = data.get('user_id')
            
            if not theme_id or not user_id:
                return {'status': 'error', 'message': 'Données manquantes'}

            # Récupère les questions
            questions = self.db.get_questions_for_game(theme_id)
            formatted_questions = []
            used_questions = set()  # Pour suivre les questions déjà utilisées

            # Fonction pour ajouter des questions uniques
            def add_unique_questions(question_list, count):
                added = []
                for q in question_list:
                    question_text = q[4]
                    if question_text not in used_questions and len(added) < count:
                        used_questions.add(question_text)
                        added.append(q)
                return added

            # Ajoute les questions selon leur type
            if QuestionType.OPEN in questions:
                formatted_questions.extend(add_unique_questions(questions[QuestionType.OPEN], 5))
            if QuestionType.QUAD in questions:
                formatted_questions.extend(add_unique_questions(questions[QuestionType.QUAD], 10))
            if QuestionType.DUAL in questions:
                formatted_questions.extend(add_unique_questions(questions[QuestionType.DUAL], 20))

            if not formatted_questions:
                return {'status': 'error', 'message': 'Pas assez de questions disponibles'}

            random.shuffle(formatted_questions)
            
            game_id = f"game_{int(time.time())}_{user_id}"
            self.active_games[game_id] = {
                'questions': formatted_questions,
                'current_index': 0,
                'score': 0,
                'user_id': user_id,
                'answers_history': [],
                'start_time': time.time()
            }

            return {
                'status': 'success',
                'game_id': game_id,
                'question': formatted_questions[0]
            }
            
        except Exception as e:
            print(f"Erreur start_game: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_submit_answer(self, data, client_socket):
        """Gère la soumission d'une réponse"""
        try:
            game_id = data.get('game_id')
            answer = data.get('answer')
            time_taken = data.get('time_taken', 30)
            
            if game_id not in self.active_games:
                return {'status': 'error', 'message': 'Partie non trouvée'}
                
            game = self.active_games[game_id]
            current_question = game['questions'][game['current_index']]
            
            # Si la question est passée
            if answer is None:
                points = 0
                is_correct = False
            else:
                # Vérifie la réponse (insensible à la casse)
                is_correct = False
                if current_question[2] == QuestionType.OPEN.value:
                    is_correct = is_correct_answer(answer, current_question[5])
                else:
                    is_correct = answer.lower() == current_question[5].lower()
                
                points = current_question[3]
                if is_correct:
                    time_bonus = max(0, (30 - time_taken) / 30 * 0.2)
                    points = int(points * (1 + time_bonus))
                    game['score'] += points
            
            game['answers_history'].append({
                'question': current_question[4],
                'user_answer': answer,
                'correct_answer': current_question[5],
                'is_correct': is_correct,
                'points': points,
                'time_taken': time_taken
            })
            
            game['current_index'] += 1
            next_question = None
            if game['current_index'] < len(game['questions']):
                next_question = game['questions'][game['current_index']]
            
            return {
                'status': 'success',
                'is_correct': is_correct,
                'correct_answer': current_question[5],
                'points': points,
                'time_taken': time_taken,
                'next_question': next_question,
                'game_finished': next_question is None
            }
            
        except Exception as e:
            print(f"Erreur submit_answer: {e}")
            return {'status': 'error', 'message': str(e)}
        
    def handle_get_game_summary(self, data):
        """Récupère le résumé d'une partie"""
        try:
            game_id = data.get('game_id')
            if game_id not in self.active_games:
                return {'status': 'error', 'message': 'Partie non trouvée'}
            
            game = self.active_games[game_id]
            total_time = sum(answer['time_taken'] for answer in game['answers_history'])
            average_time = total_time / len(game['answers_history']) if game['answers_history'] else 0
            
            # Sauvegarde le score avec le temps moyen
            self.db.save_score(
                game['user_id'],
                game['questions'][0][1],  # theme_id
                game['score'],
                average_time
            )
            
            return {
                'status': 'success',
                'score': game['score'],
                'total_time': total_time,
                'average_time': average_time,
                'history': game['answers_history']
            }
        except Exception as e:
            print(f"Erreur get_game_summary: {e}")
            return {'status': 'error', 'message': str(e)}
    def handle_create_duel_room(self, data):
        """Crée un salon de duel"""
        try:
            theme_id = data.get('theme_id')
            user_id = data.get('user_id')
            if not theme_id or not user_id:
                return {'status': 'error', 'message': 'Données manquantes'}
            
            # Génère un code unique de 4 chiffres
            while True:
                room_code = str(random.randint(1000, 9999))
                if room_code not in self.duel_rooms:
                    break
            
            # Crée le salon
            self.duel_rooms[room_code] = {
                'theme_id': theme_id,
                'players': [user_id],  # Le créateur est le premier joueur
                'max_players': 6,
                'status': 'waiting',  # waiting, playing, finished
                'questions': [],  # Sera rempli au démarrage
                'scores': {}
            }
            
            return {'status': 'success', 'room_code': room_code}
        except Exception as e:
            print(f"Erreur create_duel_room: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_join_duel_room(self, data):
        """Rejoint un salon de duel"""
        try:
            room_code = data.get('room_code')
            user_id = data.get('user_id')
            
            if not room_code or not user_id:
                return {'status': 'error', 'message': 'Données manquantes'}
            
            room = self.duel_rooms.get(room_code)
            if not room:
                return {'status': 'error', 'message': 'Salon introuvable'}
            
            if room['status'] != 'waiting':
                return {'status': 'error', 'message': 'Le salon n\'accepte plus de joueurs'}
            
            if len(room['players']) >= room['max_players']:
                return {'status': 'error', 'message': 'Le salon est complet'}
            
            if user_id in room['players']:
                return {'status': 'error', 'message': 'Vous êtes déjà dans ce salon'}
            
            room['players'].append(user_id)
            return {'status': 'success', 'message': 'Salon rejoint avec succès'}
        except Exception as e:
            print(f"Erreur join_duel_room: {e}")
            return {'status': 'error', 'message': str(e)}    
    def handle_get_leaderboard(self, data):
        """Récupère le classement"""
        try:
            theme_id = data.get('theme_id')
            scores = self.db.get_leaderboard(theme_id)
            return {
                'status': 'success',
                'scores': scores
            }
        except Exception as e:
            print(f"Erreur get_leaderboard: {e}")
            return {'status': 'error', 'message': str(e)}
    def handle_get_room_players(self, data):
        """Récupère la liste des joueurs dans un salon"""
        try:
            room_code = data.get('room_code')
            if not room_code:
                return {'status': 'error', 'message': 'Code de salon manquant'}
            
            room = self.duel_rooms.get(room_code)
            if not room:
                return {'status': 'error', 'message': 'Salon introuvable'}
            
            # Récupère les noms des joueurs
            players = []
            # Crée un nouveau curseur pour cette opération
            with self.db.conn:
                cursor = self.db.conn.cursor()
                for player_id in room['players']:
                    cursor.execute('''
                    SELECT username FROM users WHERE user_id = ?
                    ''', (player_id,))
                    result = cursor.fetchone()
                    if result:
                        players.append({
                            'user_id': player_id,
                            'username': result[0],
                            'is_host': player_id == room['players'][0]
                        })
            
            response = {
                'status': 'success',
                'players': players,
                'is_host': data.get('user_id') == room['players'][0],
                'game_started': room['status'] == 'playing',
                'theme_id': room['theme_id']
            }
            
            # Si la partie a démarré, ajoute les informations nécessaires
            if room['status'] == 'playing':
                game_id = f"duel_{room_code}_{data.get('user_id')}_{int(time.time())}"
                if data.get('user_id') in room['players']:  # Vérifie que le joueur est dans la partie
                    if game_id not in self.active_games:  # Crée le jeu s'il n'existe pas déjà
                        self.active_games[game_id] = {
                            'questions': room['questions'].copy(),
                            'current_index': 0,
                            'score': 0,
                            'user_id': data.get('user_id'),
                            'room_code': room_code,
                            'answers_history': [],
                            'start_time': time.time(),
                            'theme_id': room['theme_id']
                        }
                    response['game_id'] = game_id
                    response['first_question'] = room['questions'][0] if room['questions'] else None
                
            return response
        except Exception as e:
            print(f"Erreur get_room_players: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_start_duel(self, data):
        """Démarre une partie en mode duel"""
        try:
            room_code = data.get('room_code')
            user_id = data.get('user_id')
            
            room = self.duel_rooms.get(room_code)
            if not room:
                return {'status': 'error', 'message': 'Salon introuvable'}
            
            if user_id != room['players'][0]:
                return {'status': 'error', 'message': 'Seul l\'hôte peut démarrer la partie'}
            
            if len(room['players']) < 2:
                return {'status': 'error', 'message': 'Il faut au moins 2 joueurs pour démarrer'}
            
            room['status'] = 'playing'
            # Initialisation des questions comme dans une partie normale
            questions = self.db.get_questions_for_game(room['theme_id'])
            formatted_questions = []
            used_questions = set()

            if QuestionType.OPEN in questions:
                formatted_questions.extend(self.add_unique_questions(questions[QuestionType.OPEN], 5, used_questions))
            if QuestionType.QUAD in questions:
                formatted_questions.extend(self.add_unique_questions(questions[QuestionType.QUAD], 10, used_questions))
            if QuestionType.DUAL in questions:
                formatted_questions.extend(self.add_unique_questions(questions[QuestionType.DUAL], 20, used_questions))

            random.shuffle(formatted_questions)
            
            # Initialise la partie pour chaque joueur
            for player_id in room['players']:
                game_id = f"duel_{room_code}_{player_id}_{int(time.time())}"
                self.active_games[game_id] = {
                    'questions': formatted_questions.copy(),
                    'current_index': 0,
                    'score': 0,
                    'user_id': player_id,
                    'room_code': room_code,
                    'answers_history': [],
                    'start_time': time.time(),
                    'theme_id': room['theme_id']  # Ajout du theme_id ici
                }
                room['scores'][player_id] = 0

            room['questions'] = formatted_questions
            room['current_question_index'] = 0
            
            return {
                'status': 'success',
                'message': 'La partie va commencer',
                'first_question': formatted_questions[0],
                'game_id': f"duel_{room_code}_{user_id}_{int(time.time())}",
                'theme_id': room['theme_id']  # Ajout du theme_id ici aussi
            }
        except Exception as e:
            print(f"Erreur start_duel: {e}")
            return {'status': 'error', 'message': str(e)}

    def add_unique_questions(self, question_list, count, used_questions):
        """Helper pour ajouter des questions uniques"""
        added = []
        for q in question_list:
            question_text = q[4]
            if question_text not in used_questions and len(added) < count:
                used_questions.add(question_text)
                added.append(q)
        return added       

def initialize_test_data(db):
    """Initialise les données de test"""
    themes = [
        "Histoire",
        "Sciences",
        "Géographie",
        "Sport",
        "Culture Générale"
    ]
    
    for theme_name in themes:
        db.cursor.execute("INSERT OR IGNORE INTO themes (theme_name) VALUES (?)", (theme_name,))
    
    theme_ids = {}
    for theme_name in themes:
        db.cursor.execute("SELECT theme_id FROM themes WHERE theme_name = ?", (theme_name,))
        theme_ids[theme_name] = db.cursor.fetchone()[0]
        test_questions = {
        "Histoire": [
            {
                "type": QuestionType.DUAL,
                "question": "La Seconde Guerre mondiale a-t-elle commencé en 1939?",
                "correct": "Oui",
                "wrong": ["Non"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a découvert l'Amérique?",
                "correct": "Christophe Colomb",
                "wrong": ["Marco Polo", "Vasco de Gama", "Magellan"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "En quelle année la Révolution française a-t-elle commencé ?",
                "correct": "1789",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Qui a été le premier empereur de France ?",
                "correct": "Napoléon",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "En quelle année a eu lieu la Révolution russe ?",
                "correct": "1917",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle civilisation a construit les Pyramides",
                "correct": "Égyptiens",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Qui a été le premier empereur de Rome",
                "correct": "Auguste",
                "wrong": []
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a été le premier PRésident des États-Unis?",
                "correct": "George Washington",
                "wrong": ["Abraham Lincoln", "Thomas Jefferson", "Franklin Rosevelt"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle bataille a eu lieu en 1066",
                "correct": "Bataille d'Hastings",
                "wrong": ["Bataille de Waterloo", "Bataille de Normanide", "Bataille de Gaugamela"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a été le premier ministre du Royaaume-Uni pendant la Seconde Guerre mondiale ?",
                "correct": "Winston Churchill",
                "wrong": ["Neville Chamberlain", "Clement Attlee", "David Cameron"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "En quelle anné a été signé le traité de Versailles ?",
                "correct": "1919",
                "wrong": ["1914", "1939", "1945"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a fondé l'Empire Mongol ?",
                "correct": "Gengis Khan",
                "wrong": ["Kublai Khan", "Attila le Hun", "Tamerlan"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel évènement a marqué la fin de l'empire romain d'Occident",
                "correct": "La chute de Rome en 476",
                "wrong": ["Bataille de Hastings", "La conquête de Constantinople", "Le sac de ROme par les Gaulois"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui était le leader de l'URSS pendanrt la crise des missiles de Cuba",
                "correct": "Nikita Krouchtchev",
                "wrong": ["Joseph Staline", "Leonid Brejnev", "Mikhail Gorbatchev"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel évènement a marqué le début de la Révolution Industrielle ?",
                "correct": "L'invention de la machine à vapeur",
                "wrong": ["La découverte de l'électricité", "L'invention de l'ampoule", "L'invention du téléphone"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "En quelle anné a eu lieu le débarquement en Normandie",
                "correct": "1944",
                "wrong": ["1943", "1940", "1918"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Qui a été le denrier roi de France ?",
                "correct": "Charles X",
                "wrong": ["Louis XVI"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel pays a été le principal adversaire de Napoléon Bonaparte lors de sguerres napoléoniennes",
                "correct": "Royaume-Uni",
                "wrong": ["Prusse"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel traité a mit fin à la Première Guerre mondiale",
                "correct": "Traité de Versailles",
                "wrong": ["Traité de Paris"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Qui a mené la conquête de l'Égypte par les Romains ?",
                "correct": "Jules César",
                "wrong": ["Octave"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel empereur romain a divisé l'Empire en deux parties ?",
                "correct": "Dioclétien",
                "wrong": ["Augustus"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel évènement a conduit à la fin de la monarchie absolue en France",
                "correct": "Révolutoin français",
                "wrong": ["Abolition de l'esclavagisme"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Qui a écrit << Le Prince >> au XVIe siècle ?",
                "correct": "Nicolas Machiavel",
                "wrong": ["Jean Bodin"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Qui a été le dirigeant de l'Allemagne nazie pendant la Seconde Guerre mondiale ?",
                "correct": "Adolf Hitler",
                "wrong": ["Kaiser Wilhelm II"]
            },

        ],
        "Sciences": [
            {
                "type": QuestionType.DUAL,
                "question": "L'eau bout-elle à 100°C au niveau de la mer?",
                "correct": "Oui",
                "wrong": ["Non"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel est le symbole chimique de l'or?",
                "correct": "Au",
                "wrong": ["Ag", "Fe", "Cu"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle est la vitesse de la lumière en km/s?",
                "correct": "299792",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "D’après Charles Darwin, quel phénomène permet à chaque espèce de s’adapter à son environnement par une transmission des gènes avantageux ?",
                "correct": "Sélection naturelle",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le symbole chimique du Potassium ?",
                "correct": "K",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "En géographie, combien y'a t-il de fuseaux horaires ?",
                "correct": "24",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle membrane tapissant le fond de l’œil nous sert à capter les images et la lumière ?",
                "correct": "La rétine",
                "wrong": []
            },
            {
                "type": QuestionType.DUAL,
                "question": "Après l’éléphant, quel animal terrestre est le plus lourd ? ",
                "correct": "rhinocéros",
                "wrong": ["hippopotame"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le nom complet de l’organisation spatiale américaine connue sous le sigle NASA ?",
                "correct": "National Aeronautics and Space Administration",
                "wrong": ["National aeronautics and Space America "]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Le joule est une unité de mesure …",
                "correct": "d'énergie",
                "wrong": ["de puissance"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Lors de la combustion, le combustible réagit avec…",
                "correct": "un comburant",
                "wrong": ["un carburant"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Dans un triangle rectangle, le carré de la longueur de l’hypoténuse est égal à…",
                "correct": "la somme des carrés de ses deux autres côtés",
                "wrong": ["la somme de la longueur de ses autres côtés"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Qu’est qu’une « zone de subduction » ?",
                "correct": "L’endroit où une plaque tectonique plonge sous une autre",
                "wrong": ["Le lieu où se forment les cyclones"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quelle est l’épaisseur moyenne de l’atmosphère terrestre ?",
                "correct": "600 km",
                "wrong": ["100 km"]
            },

            {
                "type": QuestionType.DUAL,
                "question": "Quel élément chimique a pour symbole la lettre N ?",
                "correct": "Azote",
                "wrong": ["Néptunium"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Comment appelle-t-on un réseau internet hertzien (sans fil) ?",
                "correct": "Hertzien",
                "wrong": ["TNT"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Le centre de contrôle hormonal humain est :",
                "correct": "L’hypothalamus",
                "wrong": ["Le foie", "Le coeur", "l'épiphyse"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel scientifique a énoncé la loi de gravitation ?",
                "correct": "Isaac Newton",
                "wrong": ["Nikola Tesla", "Johannes Kepler", "Huygens"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "On attribue la phrase : «Rien ne se perd, tout se transforme» à :",
                "correct": "Antoine Lavoisier",
                "wrong": ["Robert Boyle", "Amadéo Avogadro", "Albert Einstein"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "De qui sont les quatre équations qui décrivent le comportement et les relations du champ électromagnétique ainsi que son interaction avec la matière ?",
                "correct": "Maxwell",
                "wrong": ["Fabre", "Chakaroun", "Becquerel"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "En réseaux, un réseau local est défini par quel sigle ?",
                "correct": "LAN",
                "wrong": ["WOMAN", "MAN", "WAN"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Le système d’assurance maladie de type beveridgien a pour pays d’origine :",
                "correct": "Le Royaume-Uni",
                "wrong": ["Allemagne", "France", "Suisse"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Pour laquelle de ces maladies aucun vaccin n’est-il disponible ?",
                "correct": "VIH",
                "wrong": ["grippe", "Rougeole", "Varicelle"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Les diurétiques sont des médicaments :",
                "correct": "Augmentant les urines",
                "wrong": ["Augmentant les selles", "Augmentant la pression artérielle", "Augmentant la pression veineuse"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel câble est utilisé dans la fibre optique ? ",
                "correct": "Câble en fibre de verre",
                "wrong": ["Câble en cuivre", "Câble coaxial", "Câble à paire torsadée"]
            },
        ],
        "Géographie": [
            {
                "type": QuestionType.DUAL,
                "question": "Le Nil est-il le plus long fleuve du monde?",
                "correct": "Oui",
                "wrong": ["Non"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la capitale de l'Australie?",
                "correct": "Canberra",
                "wrong": ["Sydney", "Melbourne", "Perth"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "Combien y a-t-il de continents ?",
                "correct": "7",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle est la capitale de l'Australie",
                "correct": "Canberra",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le fleuve le plus long du monde ?",
                "correct": "Amazone",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le désert le plus grand du monde ?",
                "correct": "Sahara",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle montagne est la plus haute du monde ?",
                "correct": "Everest",
                "wrong": []
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel océan est le plus grand ?",
                "correct": "Pacifique",
                "wrong": ["Atlantique"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quelle est la plus grande île du monde ?",
                "correct": "Groenland",
                "wrong": ["Madagascar"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel pays possède le plus de lacs ?",
                "correct": "Canada",
                "wrong": ["Russie"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le continent le plus peuplé ?",
                "correct": "Asie",
                "wrong": ["Afrique"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quelle est la mer la plus salée ?",
                "correct": "Mer Morte",
                "wrong": ["Mer Rouge"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est la plus petite nation du monde ?",
                "correct": "Vatican",
                "wrong": ["Monaco"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le point le plus bas sur Terre ?",
                "correct": "Mer Morte",
                "wrong": ["Vallée de la Mort"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le pljus grand pays du monde en superficie ?",
                "correct": "Russie",
                "wrong": ["Chine"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la capitale de l'Argentine",
                "correct": "Buenos Aires",
                "wrong": ["Lima", "Montevideo", "Santiago"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est lae plus petit continent en superficie ?",
                "correct": "Europe",
                "wrong": ["Amérique du Sud", "Australie", "Océanie"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel fleuve traverse la ville de Paris ?",
                "correct": "Seine",
                "wrong": ["Rhin", "Loire", "Tamise"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle chaîne dem ontagne est la pljus longue du monde ?",
                "correct": "Andes",
                "wrong": ["Himalaya", "Rocheuses", "Alpes"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la plus grande mer intérieure du monde ?",
                "correct": "Mer Caspienne",
                "wrong": ["Mer Méditerranée", "Mer Noire", "Mer Rouge"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel pays es t traversé par le Nil Bleu ?",
                "correct": "Éthiophie",
                "wrong": ["Ouganda", "Égypte", "Soudan"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel pays a le plus de frontières terrestrres ?",
                "correct": "Chine",
                "wrong": ["Brésil", "Inde", "Russie"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel est le plus grand désert froid du monde ?",
                "correct": "Antarctique",
                "wrong": ["Sahara", "Arctique", "Gobi"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle Ville est surnomée la ville éternelle",
                "correct": "Rome",
                "wrong": ["Jérusalem", "Athènes", "Istanbul"]
            },
        ],
        "Sport": [
            {
                "type": QuestionType.DUAL,
                "question": "Le football se joue-t-il à 11 contre 11?",
                "correct": "Oui",
                "wrong": ["Non"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel pays a gagné le plus de Coupes du Monde de football?",
                "correct": "Brésil",
                "wrong": ["Allemagne", "Italie", "Argentine"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "Combien de joueurs composent une équipe de basketball sur le terrain?",
                "correct": "5",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le club détenant le plus de défaites d’affilée en Ligue des Champions ? ",
                "correct": "Marseille",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel pays a remporté le plus de médailles dans l’histoire des jeux olympiques ?",
                "correct": "Étas-Unis",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le meilleur buteur de l'histoire de la premier league ? ",
                "correct": "Alan Shearer",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle est l’année  de création du PSG ? ",
                "correct": "1970",
                "wrong": []
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel pays a remporté la Coupe du Monde de football 2018 ?",
                "correct": "France",
                "wrong": ["Allemagne", "Italie", "Argentine"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la hauteur d'un filet dans un match de volleyball masculin ?",
                "correct": "2,43 m",
                "wrong": ["2,24 m", "2,50 m ", "2,15"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a remporté le Ballon d'Or en 2022 ?",
                "correct": "Benzema",
                "wrong": ["Messi", "Modric", "Hakimi"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Dans quelle ville se déroule le marathon le plus célèbre du monde ?",
                "correct": "Boston",
                "wrong": ["Paris", "Tokyo", "Alger"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la discipline sportive de Simone Biles ?",
                "correct": "Gymnastique artistique",
                "wrong": ["Natation", "Tennis", "Patinage artistique"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel est le poste du basketteur Tony Parker ?",
                "correct": "Menuer",
                "wrong": ["Pivot", "Ailier fort", "Arrière"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel héros de cartoon affronte Michael Jordan dans le film « Space Jam » ?",
                "correct": "Buggs Bunny",
                "wrong": ["Looney Tunes", "Jerry", "Stich"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel est le nom de l’entraîneur de l’équipe masculine de France de basket depuis 2009 ?",
                "correct": "Vincent Collet",
                "wrong": ["Belarbi Wassim", "Pierre Vincent", "Jacques Monclar"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel a été le match le plus long de l'histoire de Roland Garros ?",
                "correct": "Santoro contre Clément",
                "wrong": ["Nadal contre Federer", "Nadal contre Djokovic", "Noah contre Lendl"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Depuis 2011, combien de fois l’Olympique de Marseille a gagné contre le PSG ?",
                "correct": "1 fois",
                "wrong": ["2 fois"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le premier pays africain à atteindre les quarts de finale de coupe du monde ? ",
                "correct": "Cameroun",
                "wrong": ["Nigéira"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel fut le score de la confrontation entre l'Algérie et le Maroc en 2011 à Marrakech (Victoire du Maroc évidemment) ",
                "correct": "4-0",
                "wrong": ["3-0"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel joueur est surnommé El Flaco ?",
                "correct": "Javier Pastore",
                "wrong": ["Ezequiel Lavezzi"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel joueur met le troisième but en pleine lucarne lors de la fameuse victoire 4-0 du FC Barcelone contre le Réal Madrid en 2015 ?",
                "correct": "Andres Iniesta",
                "wrong": ["Luis Suarez"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel joueur de tennis détient le record de titres en Grand Chelem (en simple) chez les hommes en 2023 ?",
                "correct": "Novak Djokovic",
                "wrong": ["Roger Federer"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel joueur de basket a été le plus jeune MVP de l'histoire de la NBA ?",
                "correct": "Lebron James",
                "wrong": ["Derrick Rose"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "En Formule 1, quelle écurie a remporté le plus de titres constructeurs ?",
                "correct": "Ferrari",
                "wrong": ["McLaren"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel nageur détient le record du plus grand nombre de médailles olympiques dans l'histoire ?",
                "correct": "Michael Phelps",
                "wrong": ["Mark Spitz"]
            }
        ],
        "Culture Générale": [
            {
                "type": QuestionType.DUAL,
                "question": "La Joconde est-elle au Louvre?",
                "correct": "Oui",
                "wrong": ["Non"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui a peint la Joconde?",
                "correct": "Leonard de Vinci",
                "wrong": ["Michel-Ange", "Raphaël", "Botticelli"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "En quelle année est mort Mozart?",
                "correct": "1791",
                "wrong": []
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quelle est la langue officielle du Vatican ?",
                "correct": "LAtin",
                "wrong": ["Italien"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le nom de la monnaie utilisée dans le jeu Monopoly ?",
                "correct": "Dollars Monopoly",
                "wrong": ["Euro"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Dans quel domaine excelle le chef cuisinier Gordon Ramsay ?",
                "correct": "Cuisine",
                "wrong": ["Pâtisserie"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le nom de l'arme emblématique de James Bond ?",
                "correct": "Walther PPK",
                "wrong": ["Beretta"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel instrument utilise un chef d'orchestre pour diriger les musiciens ?",
                "correct": "Baguette",
                "wrong": ["Archet"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel est le jeu de société où l'on peut devenir « détective » pour résoudre un meurtre ?",
                "correct": "Cluedo",
                "wrong": ["Scrabble"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Dans quel sport est attribué le trophée Larry O'Brien ?",
                "correct": "Basketball",
                "wrong": ["Tennis"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quel célèbre magicien est connu pour son tour « de l’évasion » ?",
                "correct": "Harry Houdini",
                "wrong": ["David Copperfield"]
            },
            {
                "type": QuestionType.DUAL,
                "question": "Quelle couleur obtient-on en mélangeant du bleu et du jaune ?",
                "correct": "Vert",
                "wrong": ["Violet"]
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le prénom du personnage principal dans le roman Madame Bovary ?",
                "correct": "Emma",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel film a remporté l'Oscar du meilleur film en 1998 ?",
                "correct": "Titanic",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quelle est la capitale de la mode en Italie ?",
                "correct": "Milan",
                "wrong": []
            },
            {
                "type": QuestionType.OPEN,
                "question": "Quel est le plat principal traditionnel de l'Espagne ?",
                "correct": "Paella",
                "wrong": []
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel auteur a écrit Les Misérables ?",
                "correct": "Victor Hugo",
                "wrong": ["Flaubert", "Émile Zola", "Botticelli"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle série met en scène les familles Stark, Lannister et Targaryen ?",
                "correct": "Games of Thrones",
                "wrong": ["Breaking Bad", "The Witcher", "VIkings"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel peintre est célèbre pour ses nénuphars ?",
                "correct": "Claude Monet",
                "wrong": ["Salvador Dali", "Pablo Picasso", "Paul Cézanne"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel est le nombre total de cases sur un échiquier ?",
                "correct": "64",
                "wrong": ["48", "54", "100"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la devise nationale de la France ?",
                "correct": "Liberté Égalité Fraternité",
                "wrong": ["Égalité Fraternité Solidarité", "Justice Liberté Respect", "Liberté Impôts RSA"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Qui est l'inventeur de l'imprimerie moderne ?",
                "correct": "Johannes Gutenberg",
                "wrong": ["Isaac Newton", "Thomas Edison", "Léonard de Vinci"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel acteur incarne Jack dans Titanic ?",
                "correct": "Leonardo DiCaprio",
                "wrong": ["Brad Pitt", "Tom Cruise", "Depardieu"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quelle est la boisson nationale du Japon ?",
                "correct": "Saké",
                "wrong": ["Bissap", "Atay", "Thé Matcha"]
            },
            {
                "type": QuestionType.QUAD,
                "question": "Quel super-héros est connu pour son amour des tacos ?",
                "correct": "Deadpool",
                "wrong": ["Batman", "Spider-Man", "Superman"]
            },



        ]
    }

    # Ajout des questions dans la base de données
    for theme_name, questions in test_questions.items():
        theme_id = theme_ids[theme_name]
        for q in questions:
            db.add_question(
                theme_id=theme_id,
                question_type=q["type"],
                question_text=q["question"],
                correct_answer=q["correct"],
                wrong_answers=q["wrong"]
            )

    db.conn.commit()

def main():
    try:
        server = QuizServer()
        print("Initialisation des données de test...")
        initialize_test_data(server.db)
        print("Données initialisées avec succès")
        server.start()
    except KeyboardInterrupt:
        print("\nArrêt du serveur demandé par l'utilisateur")
    except Exception as e:
        print(f"Erreur fatale du serveur: {e}")

if __name__ == "__main__":
    main()
