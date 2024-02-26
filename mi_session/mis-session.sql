use epharmacy;
 -- La liste des utilisateurs de l’application selon leur rôle
 SELECT u.full_name AS Nom_Utilisateur, r.name AS Role
FROM user u
JOIN role r ON u.role_id = r.id;

  -- Noms et quantités des produits achetés par Oumar Moussa
SELECT p.name AS Nom_Produit, ol.quantity AS Quantite_Achetee
FROM User u
WHERE u.email = 'oumar@gmail.com';
  -- Quel sont les noms de produits dont le fournisseur est basé à Moncton ?
SELECT p.name AS Nom_Produit
FROM product p
JOIN supplier s ON p.supplier_id = s.id
WHERE s.city = 'Moncton';
  
