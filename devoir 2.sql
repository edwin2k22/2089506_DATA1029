use library;

-- select title, price from titles where title like "%computer%";
 
-- select title, price from titles where title not like "SU%" or "BU%";
-- select title, price from titles where title not like 'S%' and title not like 'B%' and  title rlike "^.{1}o";

-- select title, price from titles where title not like 'S%' and title not like 'B%' and  title rlike "^.{2}f";
select title, price from titles where title rlike '^[A-J]';

 






