use library;
select *from employees;
select *from publishers;
select *from jobs;
select *from sales;
select *from stores;
select *from titleauthor;
select *from authors;
select *from titles;


-- Noms complets des employés de plus haut grade par employeurs
SELECT e.fname, e.lname, j.job_desc, p.pub_name
FROM employees AS e
JOIN publishers AS p ON e.pub_id = p.pub_id
JOIN jobs AS j ON e.job_id = j.job_id
WHERE e.job_lvl = 'SEINIOR';

--  Noms complets des employés ayant un salaire supérieur à celui de Norbert Zongo
select e.fname, e.lname, e.salary
from employees as e
where e.salary > 3;

--  Noms complets des employés des éditeurs canadiens.
select e.fname, e.lname
from employees as e
join publishers as p where country= "canada";


--  Noms complets des employés qui ont un manager
select e.fname,e.lname ;

--  Noms complets des employés qui ont un salaire au-dessus de la moyenne de la moyenne
SELECT fname, lname, salary 
from employees
where salary >= (select round(avg(salary))
 from employees);
 
--   Noms complets des employés qui ont le salaire minimum de leur grade
SELECT DISTINCT e.fname, e.lname, e.job_id, e.salary
FROM employees e
WHERE e.salary = (
    SELECT MIN(salary)
    FROM employees
    WHERE job_lvl = e.job_lvl
);


--  De quels types sont les livres les plus vendus
SELECT t.type, SUM(s.qty)
FROM sales s
JOIN titles t ON s.title_id = t.title_id
GROUP BY t.type
ORDER BY SUM(s.qty) DESC
LIMIT 1;



--  Pour chaque boutique, les 2 livres les plus vendus et leurs prix
SELECT s.stor_id, t.title_id, SUM(s.qty)
FROM sales s
JOIN titles t ON s.title_id = t.title_id
GROUP BY s.stor_id, t.title_id
ORDER BY s.stor_id, SUM(s.qty) DESC
LIMIT 2;






--  Les auteurs des 5 livres les plus vendus
SELECT a.au_id, a.au_fname, a.au_lname, SUM(s.qty)
FROM authors a
JOIN titleauthor at ON a.au_id = at.au_id
JOIN sales s ON at.title_id = s.title_id
GROUP BY a.au_id, a.au_fname, a.au_lname
ORDER BY SUM(s.qty) DESC
LIMIT 5;







--  Prix moyens des livres par maisons d’édition
SELECT pub_id, AVG(price) 
FROM titles
GROUP BY pub_id;


--  Les 3 auteurs ayant les plus de livres
SELECT au_id, COUNT(title_id) AS num_titles
FROM titleauthor
GROUP BY au_id
LIMIT 3;

