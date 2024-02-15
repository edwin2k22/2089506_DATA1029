use library;


-- 1 obtenir la liste des auteurs dont l’éditeur « Harmattan » n’a publié aucun livre
SELECT a.au_fname, a.au_lname
FROM authors a, titleauthor ta, titles t
WHERE a.au_id = ta.au_id
AND ta.title_id = t.title_id
AND t.pub_id != (SELECT pub_id FROM publishers WHERE pub_name = 'Harmattan');

-- 2 Obtenir la liste des auteurs dont l’éditeur «Eyrolles » a publié tous les livres
SELECT a.au_fname, a.au_lname
FROM authors a, titleauthor ta, titles t
WHERE a.au_id = ta.au_id
AND ta.title_id = t.title_id
AND t.pub_id = (SELECT pub_id FROM publishers WHERE pub_name = 'Eyrolles');


