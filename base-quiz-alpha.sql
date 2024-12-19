-- Table Utilisateur
CREATE TABLE Utilisateur (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    pseudo VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mot_de_passe VARCHAR(255) NOT NULL,
    score_total INT DEFAULT 0
);

-- Table Admin
CREATE TABLE Admin (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    pseudo VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mot_de_passe VARCHAR(255) NOT NULL
);

-- Table Quiz
CREATE TABLE Quiz (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(100) NOT NULL,
    thème VARCHAR(50),
    difficulté VARCHAR(20),
    durée INT NOT NULL
);

-- Table Question
CREATE TABLE Question (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    texte TEXT NOT NULL,
    type_question ENUM('2 choix', '4 choix', 'sans proposition') NOT NULL,
    points INT NOT NULL,
    quiz_ID INT NOT NULL,
    FOREIGN KEY (quiz_ID) REFERENCES Quiz(ID) ON DELETE CASCADE
);

-- Table Réponse
CREATE TABLE Réponse (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    texte TEXT NOT NULL,
    est_correcte BOOLEAN NOT NULL,
    question_ID INT NOT NULL,
    FOREIGN KEY (question_ID) REFERENCES Question(ID) ON DELETE CASCADE
);

-- Table Score
CREATE TABLE Score (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur_ID INT NOT NULL,
    quiz_ID INT NOT NULL,
    points_obtenus INT NOT NULL,
    date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (utilisateur_ID) REFERENCES Utilisateur(ID) ON DELETE CASCADE,
    FOREIGN KEY (quiz_ID) REFERENCES Quiz(ID) ON DELETE CASCADE
);
