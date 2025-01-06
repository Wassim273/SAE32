import sqlite3
import hashlib
import time
from enum import Enum

class QuestionType(Enum):
    DUAL = 1      # Questions à 2 choix (1 point)
    QUAD = 3      # Questions à 4 choix (3 points)
    OPEN = 5      # Questions sans proposition (5 points)

class QuizDatabase:
    def __init__(self, db_name='quiz.db'):
        """Initialise la connexion à la base de données"""
        self.conn = sqlite3.connect(db_name, check_same_thread=False)  # Permet l'accès multi-thread
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Création des tables de la base de données"""
        # Table des utilisateurs
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Table des thèmes
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS themes (
            theme_id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_name TEXT UNIQUE NOT NULL
        )
        ''')

        # Table des questions
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id INTEGER,
            question_type INTEGER NOT NULL,
            points INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            wrong_answer1 TEXT,
            wrong_answer2 TEXT,
            wrong_answer3 TEXT,
            used_count INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            FOREIGN KEY (theme_id) REFERENCES themes (theme_id)
        )
        ''')

        # Table des scores
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            theme_id INTEGER,
            score INTEGER NOT NULL,
            total_time FLOAT NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (theme_id) REFERENCES themes (theme_id)
        )
        ''')

        self.conn.commit()

    def add_user(self, username, password):
        """Ajoute un nouvel utilisateur"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute('''
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            ''', (username, password_hash))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        """Vérifie les identifiants d'un utilisateur"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute('''
        SELECT user_id FROM users
        WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_question(self, theme_id, question_type, question_text, correct_answer, wrong_answers=None):
        """Ajoute une nouvelle question"""
        try:
            wrong_answer1 = wrong_answers[0] if wrong_answers else None
            wrong_answer2 = wrong_answers[1] if wrong_answers and len(wrong_answers) > 1 else None
            wrong_answer3 = wrong_answers[2] if wrong_answers and len(wrong_answers) > 2 else None

            self.cursor.execute('''
            INSERT INTO questions (
                theme_id, question_type, points, question_text, 
                correct_answer, wrong_answer1, wrong_answer2, wrong_answer3
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (theme_id, question_type.value, question_type.value, question_text,
                 correct_answer, wrong_answer1, wrong_answer2, wrong_answer3))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de l'ajout de la question: {e}")
            return False

    def get_questions_for_game(self, theme_id):
        """Récupère les questions pour une partie en évitant les répétitions"""
        questions = {
            QuestionType.OPEN: [],
            QuestionType.QUAD: [],
            QuestionType.DUAL: []
        }
        
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        for q_type in QuestionType:
            # Sélectionne les questions les moins utilisées en priorité
            self.cursor.execute('''
            SELECT * FROM questions 
            WHERE theme_id = ? AND question_type = ?
            ORDER BY used_count ASC, last_used ASC, RANDOM()
            LIMIT ?
            ''', (theme_id, q_type.value, 
                 5 if q_type == QuestionType.OPEN else 
                 10 if q_type == QuestionType.QUAD else 20))
            
            selected_questions = self.cursor.fetchall()
            questions[q_type] = selected_questions
            
            # Met à jour le compteur d'utilisation pour les questions sélectionnées
            for question in selected_questions:
                self.cursor.execute('''
                UPDATE questions 
                SET used_count = used_count + 1,
                    last_used = ?
                WHERE question_id = ?
                ''', (current_time, question[0]))
            
            self.conn.commit()
            
        return questions

    def get_all_themes(self):
        """Récupère tous les thèmes"""
        self.cursor.execute("SELECT theme_id, theme_name FROM themes")
        return self.cursor.fetchall()

    def save_score(self, user_id, theme_id, score, total_time):
        """Enregistre un score"""
        try:
            self.cursor.execute('''
            INSERT INTO scores (user_id, theme_id, score, total_time)
            VALUES (?, ?, ?, ?)
            ''', (user_id, theme_id, score, total_time))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_top_scores(self, theme_id=None, limit=10):
        """Récupère les meilleurs scores"""
        if theme_id:
            self.cursor.execute('''
            SELECT users.username, scores.score, scores.total_time
            FROM scores
            JOIN users ON scores.user_id = users.user_id
            WHERE scores.theme_id = ?
            ORDER BY scores.score DESC, scores.total_time ASC
            LIMIT ?
            ''', (theme_id, limit))
        else:
            self.cursor.execute('''
            SELECT users.username, themes.theme_name, scores.score, scores.total_time
            FROM scores
            JOIN users ON scores.user_id = users.user_id
            JOIN themes ON scores.theme_id = themes.theme_id
            ORDER BY scores.score DESC, scores.total_time ASC
            LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.conn.close()