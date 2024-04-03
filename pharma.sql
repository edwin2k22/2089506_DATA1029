use epharmcy;

use epharmacy;

select *from products;
select *from roles;
select * from users;
select * from connection_history;
select *from cart_product;
select* from invoices;
select *from warehouses;




-- 4. Noms complets et durée moyenne de connexion:
SELECT u.firstname, u.lastname, AVG(TIMESTAMPDIFF(SECOND, ch.login_date, ch.logout_date)) AS average_session_duration
FROM connection_history ch
INNER JOIN users u ON u.id = ch.user_id
GROUP BY u.id;

-- 5. Rôle de l'utilisateur ayant passé le plus de temps connecté:
SELECT r.name, AVG(TIMESTAMPDIFF(SECOND, ch.login_date, ch.logout_date)) 
FROM connection_history ch
INNER JOIN users u ON u.id = ch.user_id
INNER JOIN roles r ON r.id = u.role_id
GROUP BY r.id
ORDER BY AVG(TIMESTAMPDIFF(SECOND, ch.login_date, ch.logout_date)) DESC 
LIMIT 1; 

-- 6. Fournisseurs des 3 produits les plus commercialisés:
SELECT s.name supplier_name, p.name product_name, SUM(cp.quantity_remainder) total_sales
FROM cart_product cp
INNER JOIN products p ON p.id = cp.product_id
INNER JOIN suppliers s ON s.id = p.supplier_id
GROUP BY p.id
ORDER BY total_sales DESC
LIMIT 3;


-- 7. Chiffres d'affaires par entrepôts
SELECT w.name AS warehouse_name, SUM(o.total_amount) AS total_sales
FROM orders o
INNER JOIN cart_product cp ON o.cart_id = cp.cart_id
INNER JOIN products p ON cp.product_id = p.id
INNER JOIN warehouses w ON p.warehouse_id = w.id
GROUP BY w.name
ORDER BY total_sales DESC;

-- 8. Modifier la table products de sorte à affecter l’image “medoc.jpg” comme 
-- image par défaut aux produits médicaux
 -- ajouter l'images 
 
ALTER TABLE products
ADD image VARCHAR(125) COLLATE utf8mb4_general_ci; 

ALTER TABLE products 
ADD category VARCHAR(50); 



-- 9. Ajouter une colonne gender spécifiant le sexe des utilisateurs de  l’application. Cette colonne doit être une énumération contenant pour valeur 
-- MALE, FEMALE et OTHER. 
ALTER TABLE user ADD COLUMN gender ENUM('MALE', 'FEMALE', 'OTHER');



-- 10 Ecrire une procédure stockée spProfileImage permettant d'affecter une 
-- image de profil par défaut aux utilisateurs
-- a. Les utilisateurs MALE auront pour image male.jpg
DELIMITER // 

CREATE PROCEDURE spProfileImage()
BEGIN
    DECLARE finished INT DEFAULT FALSE;
    DECLARE v_userId INT DEFAULT 0;
    DECLARE v_gender VARCHAR(10) DEFAULT '';
    DECLARE v_imageFilename VARCHAR(255) DEFAULT '';

    DECLARE userCursor CURSOR FOR SELECT id, gender FROM users;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = TRUE;  

    OPEN userCursor;

    readLoop: LOOP
        FETCH userCursor INTO v_userId, v_gender;

        IF finished THEN
            LEAVE readLoop;
        END IF;

        -- Determine default image based on gender
        CASE v_gender
            WHEN 'MALE' THEN SET v_imageFilename = 'male.jpg';
            WHEN 'FEMALE' THEN SET v_imageFilename = 'female.jpg';
            ELSE SET v_imageFilename = 'other.jpg';
        END CASE;

        -- Update the profile image for the user
        UPDATE users 
        SET image = v_imageFilename 
        WHERE id = v_userId;

    END LOOP;

    CLOSE userCursor;
END //

DELIMITER ;



-- 11.Ajouter une contrainte a la table users afin de garantir l’unicité des adresses 
-- électroniques(email) des utilisateurs de l’application.

ALTER TABLE users
ADD CONSTRAINT unique_email UNIQUE (email);

-- 12 Effectuez sous forme de transactions toutes les insertions nécessaires pour 
-- passer les ventes représentées par la capture suivante : 
-- a. Insérer un nouvel utilisateur au nom de Alain Foka avec un mot de 
-- passe correspondant à la chaine vide

START TRANSACTION;

INSERT INTO users (firstname, lastname, password, role_id, country, email,image) 
VALUES ('Alain', 'Foka', '', 3, 'Canada', 'alain.foka@example.com',"");


COMMIT;


--  b La date de chaque commande doit être à l’instant auquel la commande 
-- est insérée
INSERT INTO orders (customer_id, order_date, total_amount, status, user_id, cart_id)
VALUES (1, NOW(), 100.00, 1, 1, 1);



-- c. Ces commandes sont éditées par l’administrateur Abdoulaye 
-- Mohamed
INSERT INTO orders (customer_id, order_date, total_amount, status, user_id, cart_id)
VALUES (1, NOW(), 100.00, 1, 2, 1);


-- d. Calculez le total de chacune des commandes et insérer
-- convenablement
UPDATE orders
SET total_amount = (
  SELECT SUM(quantity * total)
  FROM cart_product
  WHERE cart_product.cart_id = orders.cart_id
);


 -- Le taux d’impôt pour chacune des factures s’élève a 10%

SET SQL_SAFE_UPDATES = 0;
SET SQL_SAFE_UPDATES = 1;

UPDATE invoices
SET tax = montant * 0.10;


UPDATE users
SET firstname = 'Ali', lastname = 'Sani', designation = 'Comptable', adress = '415 Av. de l’Université', province = 'NB', postal_code = 'E1A3E9', phone = '4065954526', email = 'Ali@ccnb.ca'
WHERE firstname = 'Ali' AND lastname = 'Sani';


UPDATE users
SET firstname = 'Oumar', lastname = 'Moussa', designation = 'RH', adress = '1750 Rue Crevier', province = 'QC', postal_code = 'H4L2X5', phone = '5665954526', email = 'Oumar@gmail.com'
WHERE firstname = 'Oumar' AND lastname = 'Moussa';

UPDATE users
SET firstname = 'Dupon', lastname = 'Poupi', designation = 'Consultant', adress = '674 Van horne', province = 'NS', postal_code = 'B4V 4V5', phone = '7854665265', email = 'Foka@ccnb.ca'
WHERE firstname = 'Dupon' AND lastname = 'Poupi';


-- LUC ET ED

