DROP DATABASE IF EXISTS library2;

create database library3;
use library3;

CREATE TABLE Authors (
    au_id TINYINT PRIMARY KEY,
    au_lname VARCHAR(50),
    au_fname VARCHAR(50),
    phone VARCHAR(20) UNIQUE,
    address VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    zip VARCHAR(6),
    contract TEXT,
    email VARCHAR(50) UNIQUE
);


CREATE TABLE Publishers (
    pub_id TINYINT PRIMARY KEY,
    pub_name VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    email VARCHAR(50) UNIQUE CHECK (email LIKE '%@%')
);

CREATE TABLE Jobs (
    job_id TINYINT PRIMARY KEY,
    job_desc VARCHAR(50),
    min_lvl ENUM('Stagiaire', 'Junior', 'Intermediaire', 'Seinior'),
    max_lvl ENUM('Stagiaire', 'Junior', 'Intermediaire', 'Seinior')
);

CREATE TABLE Employees (
    emp_id TINYINT PRIMARY KEY,
    emp_name VARCHAR(50),
    salary SMALLINT,
    fname VARCHAR(50),
    lname VARCHAR(50),
    job_id SMALLINT REFERENCES Jobs(job_id),
    pub_id SMALLINT REFERENCES Publishers(pub_id),
    pub_date DATE,
    email VARCHAR(50) UNIQUE CHECK (email LIKE '%@%')
);

CREATE TABLE Titles (
    title_id TINYINT PRIMARY KEY,
    title VARCHAR(100),
    type ENUM('Roman', 'Politique', 'Science', 'Histoire'),
    pub_id SMALLINT,
    price FLOAT,
    advance FLOAT,
    notes VARCHAR(255),
    pub_date DATE,
    FOREIGN KEY (pub_id) REFERENCES Publishers(pub_id)
);

CREATE TABLE Redactions (
    au_id TINYINT REFERENCES Authors(au_id),
    title_id TINYINT REFERENCES Titles(title_id),
    au_ord TINYINT,
    royalty FLOAT,
    PRIMARY KEY (au_id, title_id)
);

CREATE TABLE Stores (
    stor_id TINYINT PRIMARY KEY,
    stor_name VARCHAR(50),
    stor_address VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50)
);

CREATE TABLE Sales (
    store_id TINYINT REFERENCES Stores(stor_id),
    ord_num TINYINT,
    title_id SMALLINT REFERENCES Titles(title_id),
    ord_date TIMESTAMP,
    qty INT,
    PRIMARY KEY (store_id, ord_num)
);





