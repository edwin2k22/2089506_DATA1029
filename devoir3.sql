use library;

-- 1. La liste des paires (auteur, éditeur) demeurant dans la même ville.
select a.au_fname as auteur, p.pub_name as editeur
from authors a
join publishers p on a.city = p.city;

 -- 2La liste des paires (auteur, éditeur) demeurant dans la même ville, incluant aussi les auteurs qui ne répondent pas à ce critère.
select a.au_fname as auteur, p.pub_name as editeur
from authors a
left join  publishers p on a.city = p.city;

-- 3. La liste des paires (auteur, éditeur) demeurant dans la même ville, incluant les auteurs et les éditeurs qui ne répondent pas à ce critère.
select a.au_fname as auteur, p.pub_name as editeur
from authors a
join publishers p on a.city = p.city;

-- 4. La liste des paires (auteur, éditeur) demeurant dans la même ville, incluant les auteurs et les éditeurs qui ne répondent pas à ce critère.
select a.au_fname as auteur, p.pub_name as editeur
from authors a
left join publishers p on a.city = p.city
union


 -- 5 Liste des employés par maison d'édition.
select e.fname as employe, p.pub_name as maison_edition
from employees e
join publishers p on e.pub_id = p.pub_id;

-- 6. Salaires horaires moyens des employés par maison d'édition 
select  p.pub_name as maison_edition, avg(e.salary) as salaire_moyen
from employees e
join  publishers p on e.pub_id = p.pub_id
group by p.pub_name;




