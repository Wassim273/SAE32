import socket
import threading
import json
from quiz_database import QuizDatabase, QuestionType
import time
import random

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
                    is_correct = answer.lower().strip() == current_question[5].lower().strip()
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
                "question": "En quelle année la Révolution française a-t-elle commencé?",
                "correct": "1789",
                "wrong": []
            }
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
            }
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
                "question": "Combien y a-t-il de continents?",
                "correct": "7",
                "wrong": []
            }
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
            }
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