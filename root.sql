use epharmacy;
-- 1. Dressez le schéma relationnel de la base de données.

-- carts(id, user_id, actif)
-- cart_product(cart_id, product_id, quantity, total, tax, quantity_remainder)
-- connection_history(id, login_date, logout_date, onsite_time, user_id)
-- invoices(id, montant, tax, users_id)
-- invoice_elements(id, invoice_id, stocks_id)
-- orders(id, customer_id, order_date, total_amount, status, user_id, cart_id)
-- products(id, name, description, code_product, supplier_id, warehouse_id, image, min_quantity, price)
-- roles(id, name, description)
-- stocks(id, name, expire_date)
-- stock_product(stock_id, product_id, quantity)
-- suppliers(id, name, adress, city, province, country, postal_code, phone, email)
-- users(id, firstname, lastname, designation, adress, city, province, country, postal_code, phone, email, password, actif, image, role_id)
-- warehouses(id, name, adress, city, province, country)

-- 2. A quoi servent les instructions des lignes 12 et 440 dans le fichier epharmacy.sql?
--  ligne 12 désactive la vérification des clés étrangères pour permettre l'importation des données tandis que la 440 donne entierement la base de données

-- 3 Créez l’utilisateur pharma avec pour mot de passe 1234
CREATE USER 'pharma'@'localhost' IDENTIFIED BY '1234';


-- Octroyer les privilèges à l'utilisateur pharma
grant select, delete,insert,update on epharmacy.cart_product to 'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.users to 'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.connection_history to 'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.suppliers to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.warehouses to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.stocks to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.stock_product to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.roles to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.products to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.invoice_elements to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.invoices to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.orders to  'pharma'@'localhost';
grant select, delete,insert,update on epharmacy.carts to  'pharma'@'localhost';


GRANT ALL PRIVILEGES ON epharmacy.* TO 'pharma'@'localhost';
FLUSH PRIVILEGES;









 












