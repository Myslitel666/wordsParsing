-- КРИНЖ, который нужно удалять из базы
-- Слова из 2 букв
SELECT *
FROM Words
WHERE LENGTH(value) = 2
  AND value not in ('ад', 'ум', 'ус', 'яд', 'ас', 'ям', 'ос', 'вы', 'ра')
UNION ALL
-- Слова, начинающиеся на невозможную букву
SELECT *
FROM Words
WHERE SUBSTR(lower(value), 1, 1) IN ('й', 'ь', 'ъ', 'ы')
  AND value != 'йод'
  AND value != 'йога'
UNION ALL
-- Исключаем неадекватные сочетания гласных/согласных
SELECT * 
FROM Words
WHERE (
    value GLOB '[уеъыаоэяиюь][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ]'
      OR 
    value GLOB '[уеъыаоэяиюь][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ]'
      OR 
    value GLOB '[уеъыаоэяиюь][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ][бвгджзйклмнпрстфхцчшщ]'
      OR
    value GLOB '[уеъыаоэяиюь][уеъыаоэяиюь][уеъыаоэяиюь][бвгджзйклмнпрстфхцчшщ]'
      OR
    value GLOB '[уеъыаоэяиюь][уеъыаоэяиюь][уеъыаоэяиюь]'
      OR
    value GLOB '[уеъыаоэяиюь][уеъыаоэяиюь][уеъыаоэяиюь][уеъыаоэяиюь]'
)
AND value not in ('уст','акт', 'иоан', 'иоал')
UNION ALL
-- Исключаем слова, которые содержат дефис, но состоят при этом из небольшого количества букв
SELECT * FROM Words 
WHERE value LIKE '%-%'
  AND LENGTH(value) in (3,4,5)
  AND value not in ('из-за')
UNION ALL
-- Исключаем все слова, которые содержат дефис вторым или предпоследним символом
SELECT * FROM Words 
WHERE (value LIKE '_-%' AND value NOT LIKE 'в%') -- оставляем слова типа 'в-третьих';
  OR substr(value,-2,1) = '-'
UNION ALL
-- Несколько дефисов
SELECT *
FROM Words
WHERE value LIKE '%-%-%'
  AND value not in (
    'мало-по-малу',
    'ростов-на-дону',
    'рок-н-ролл',
    'рок-н-ролле',
    'свято-троице-сергиева',
    'владимир-на-клязьме',
    'точь-в-точь',
    'славянск-на-кубани'
)
UNION ALL
-- Старинные кончания на -ися, -шии, -иша
SELECT *
FROM Words
WHERE (
    substr(value,-3) = 'аще' -- аще
    AND value NOT IN ('чаще','почаще', 'слаще')
)
OR (SUBSTR(value,-3) = 'ися' AND SUBSTR(value,-4) != 'мися')
OR (
    substr(value,-3) = 'иша' -- иша
    AND value NOT IN ('клавиша','афиша')
)
OR (
    substr(value,-3) = 'ища' -- ища
    AND value NOT IN ('ища')
)
OR (
    substr(value,-3) = 'шии' -- шии
    AND (substr(value,-4,1) GLOB '[бвгджзйклмнпрстфхцчшщ]' OR LENGTH(value) = 3)
)
OR SUBSTR(value,-3) = 'ыти' -- ыти
OR substr(value,-3) = 'яще' -- яще