-- Auto-generated ingredient merge migration
-- Generated: 2026-02-16T06:44:38.237932+00:00
-- Run against the live retreat_ops.db

PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;


-- Merge group: Ajwain
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ajwain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('carom seeds'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ajwain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('carom seeds'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ajwain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('carom seeds'));
DELETE FROM ingredients WHERE lower(name) = lower('carom seeds');

-- Merge group: Amchur
UPDATE OR IGNORE ingredients SET name = 'Amchur' WHERE lower(name) = lower('dried raw mango powder') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Amchur'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried raw mango powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried raw mango powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried raw mango powder'));
DELETE FROM ingredients WHERE lower(name) = lower('dried raw mango powder');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried raw mango powder (amchur)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried raw mango powder (amchur)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Amchur')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried raw mango powder (amchur)'));
DELETE FROM ingredients WHERE lower(name) = lower('Dried raw mango powder (amchur)');

-- Merge group: Asafoetida (hing)
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Asafoetida (hing)')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Hing'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Asafoetida (hing)')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Hing'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Asafoetida (hing)')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Hing'));
DELETE FROM ingredients WHERE lower(name) = lower('Hing');

-- Merge group: Avocado
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado medium'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado medium'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Avocado medium'));
DELETE FROM ingredients WHERE lower(name) = lower('Avocado medium');

-- Merge group: Bay leaves
UPDATE OR IGNORE ingredients SET name = 'Bay leaves' WHERE lower(name) = lower('Bay leaf') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Bay leaves'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaf'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaf'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Bay leaf'));
DELETE FROM ingredients WHERE lower(name) = lower('Bay leaf');

-- Merge group: Besan
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Besan')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('gram flour'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Besan')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('gram flour'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Besan')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('gram flour'));
DELETE FROM ingredients WHERE lower(name) = lower('gram flour');

-- Merge group: Black chana
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black chana')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black chana dried'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black chana')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black chana dried'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black chana')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black chana dried'));
DELETE FROM ingredients WHERE lower(name) = lower('black chana dried');

-- Merge group: Black pepper
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black pepper')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black peppercorns'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black pepper')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black peppercorns'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black pepper')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black peppercorns'));
DELETE FROM ingredients WHERE lower(name) = lower('black peppercorns');

-- Merge group: Black tea
UPDATE OR IGNORE ingredients SET name = 'Black tea' WHERE lower(name) = lower('black tea loose leaf') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Black tea'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea loose leaf'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea loose leaf'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea loose leaf'));
DELETE FROM ingredients WHERE lower(name) = lower('black tea loose leaf');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea powder dust'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea powder dust'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('black tea powder dust'));
DELETE FROM ingredients WHERE lower(name) = lower('black tea powder dust');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('loose leaf black tea'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('loose leaf black tea'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Black tea')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('loose leaf black tea'));
DELETE FROM ingredients WHERE lower(name) = lower('loose leaf black tea');

-- Merge group: Cardamom
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cardamom pods'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cardamom pods'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cardamom pods'));
DELETE FROM ingredients WHERE lower(name) = lower('cardamom pods');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cardamom pods'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cardamom pods'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cardamom pods'));
DELETE FROM ingredients WHERE lower(name) = lower('whole cardamom pods');

-- Merge group: Cardamom powder
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('ground cardamom'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('ground cardamom'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cardamom powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('ground cardamom'));
DELETE FROM ingredients WHERE lower(name) = lower('ground cardamom');

-- Merge group: Carrots
UPDATE OR IGNORE ingredients SET name = 'Carrots' WHERE lower(name) = lower('Carrot') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Carrots'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrots')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrot'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrots')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrot'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrots')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Carrot'));
DELETE FROM ingredients WHERE lower(name) = lower('Carrot');

-- Merge group: Cashews
UPDATE OR IGNORE ingredients SET name = 'Cashews' WHERE lower(name) = lower('Cashew') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Cashews'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashew'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashew'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashew'));
DELETE FROM ingredients WHERE lower(name) = lower('Cashew');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cashew nuts'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cashew nuts'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cashews')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cashew nuts'));
DELETE FROM ingredients WHERE lower(name) = lower('cashew nuts');

-- Merge group: Cilantro
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cilantro')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh cilantro'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cilantro')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh cilantro'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cilantro')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh cilantro'));
DELETE FROM ingredients WHERE lower(name) = lower('Fresh cilantro');

-- Merge group: Cinnamon
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cinnamon')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cinnamon stick'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cinnamon')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cinnamon stick'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cinnamon')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('cinnamon stick'));
DELETE FROM ingredients WHERE lower(name) = lower('cinnamon stick');

-- Merge group: Cloves
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cloves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cloves'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cloves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cloves'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cloves')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('whole cloves'));
DELETE FROM ingredients WHERE lower(name) = lower('whole cloves');

-- Merge group: Coriander powder
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coriander powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground coriander'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coriander powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground coriander'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coriander powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground coriander'));
DELETE FROM ingredients WHERE lower(name) = lower('Ground coriander');

-- Merge group: Crushed roasted peanuts
UPDATE OR IGNORE ingredients SET name = 'Crushed roasted peanuts' WHERE lower(name) = lower('Coarsely crushed roasted peanuts') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Crushed roasted peanuts'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Crushed roasted peanuts')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coarsely crushed roasted peanuts'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Crushed roasted peanuts')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coarsely crushed roasted peanuts'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Crushed roasted peanuts')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Coarsely crushed roasted peanuts'));
DELETE FROM ingredients WHERE lower(name) = lower('Coarsely crushed roasted peanuts');

-- Merge group: Cumin seeds
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cumin seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cumin seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cumin seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera'));
DELETE FROM ingredients WHERE lower(name) = lower('Jeera');

-- Merge group: Dried coconut slices
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried coconut slices')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dry Coconut Slices'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried coconut slices')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dry Coconut Slices'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried coconut slices')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dry Coconut Slices'));
DELETE FROM ingredients WHERE lower(name) = lower('Dry Coconut Slices');

-- Merge group: Dried red chilies
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried red chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chillies'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried red chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chillies'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried red chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chillies'));
DELETE FROM ingredients WHERE lower(name) = lower('Red chillies');

-- Merge group: Drumstick
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Drumstick')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('drumsticks'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Drumstick')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('drumsticks'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Drumstick')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('drumsticks'));
DELETE FROM ingredients WHERE lower(name) = lower('drumsticks');

-- Merge group: Fenugreek powder
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('roasted fenugreek powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('roasted fenugreek powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('roasted fenugreek powder'));
DELETE FROM ingredients WHERE lower(name) = lower('roasted fenugreek powder');

-- Merge group: Fenugreek seeds
UPDATE OR IGNORE ingredients SET name = 'Fenugreek seeds' WHERE lower(name) = lower('Fenugreek') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Fenugreek seeds'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek'));
DELETE FROM ingredients WHERE lower(name) = lower('Fenugreek');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Methi seeds'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Methi seeds'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fenugreek seeds')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Methi seeds'));
DELETE FROM ingredients WHERE lower(name) = lower('Methi seeds');
-- Rename 'filter coffee' → 'Filter coffee'
UPDATE ingredients SET name = 'Filter coffee' WHERE lower(name) = lower('filter coffee');
-- Rename 'Filter Coffee' → 'Filter coffee'
UPDATE ingredients SET name = 'Filter coffee' WHERE lower(name) = lower('Filter Coffee');

-- Merge group: Frozen coconut
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen fine-textured coconut'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen fine-textured coconut'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen fine-textured coconut'));
DELETE FROM ingredients WHERE lower(name) = lower('frozen fine-textured coconut');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen shredded coconut'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen shredded coconut'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen coconut')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen shredded coconut'));
DELETE FROM ingredients WHERE lower(name) = lower('frozen shredded coconut');

-- Merge group: Garlic
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Garlic')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('garlic cloves'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Garlic')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('garlic cloves'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Garlic')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('garlic cloves'));
DELETE FROM ingredients WHERE lower(name) = lower('garlic cloves');

-- Merge group: Ginger
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ginger')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh ginger'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ginger')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh ginger'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ginger')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Fresh ginger'));
DELETE FROM ingredients WHERE lower(name) = lower('Fresh ginger');

-- Merge group: Green chilies
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chillies'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chillies'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chillies'));
DELETE FROM ingredients WHERE lower(name) = lower('Green chillies');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chili'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chili'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chili'));
DELETE FROM ingredients WHERE lower(name) = lower('Thai green chili');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chilies'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chilies'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green chilies')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Thai green chilies'));
DELETE FROM ingredients WHERE lower(name) = lower('Thai green chilies');

-- Merge group: Green mung dal
UPDATE OR IGNORE ingredients SET name = 'Green mung dal' WHERE lower(name) = lower('green moong dal') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Green mung dal'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green mung dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green moong dal'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green mung dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green moong dal'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green mung dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green moong dal'));
DELETE FROM ingredients WHERE lower(name) = lower('green moong dal');

-- Merge group: Green peas
UPDATE OR IGNORE ingredients SET name = 'Green peas' WHERE lower(name) = lower('Peas') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Green peas'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Peas'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Peas'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Peas'));
DELETE FROM ingredients WHERE lower(name) = lower('Peas');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen green peas'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen green peas'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Frozen green peas'));
DELETE FROM ingredients WHERE lower(name) = lower('Frozen green peas');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen peas'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen peas'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green peas')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('frozen peas'));
DELETE FROM ingredients WHERE lower(name) = lower('frozen peas');

-- Merge group: Ground cumin
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Roasted ground cumin'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Roasted ground cumin'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Roasted ground cumin'));
DELETE FROM ingredients WHERE lower(name) = lower('Roasted ground cumin');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera Powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera Powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Ground cumin')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Jeera Powder'));
DELETE FROM ingredients WHERE lower(name) = lower('Jeera Powder');

-- Merge group: Kasuri methi
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried fenugreek leaves'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried fenugreek leaves'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('dried fenugreek leaves'));
DELETE FROM ingredients WHERE lower(name) = lower('dried fenugreek leaves');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried fenugreek leaves (kasuri methi)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried fenugreek leaves (kasuri methi)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Kasuri methi')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Dried fenugreek leaves (kasuri methi)'));
DELETE FROM ingredients WHERE lower(name) = lower('Dried fenugreek leaves (kasuri methi)');

-- Merge group: Khakhra
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakhra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakra'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakhra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakra'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakhra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Khakra'));
DELETE FROM ingredients WHERE lower(name) = lower('Khakra');

-- Merge group: Lemon or lime
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime juice'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime juice'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime juice'));
DELETE FROM ingredients WHERE lower(name) = lower('Lemon or lime juice');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lime or lemon'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lime or lemon'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lemon or lime')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Lime or lemon'));
DELETE FROM ingredients WHERE lower(name) = lower('Lime or lemon');

-- Merge group: Masoor dal
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Masoor dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('split masoor dal'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Masoor dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('split masoor dal'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Masoor dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('split masoor dal'));
DELETE FROM ingredients WHERE lower(name) = lower('split masoor dal');

-- Merge group: Mint
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint'));
DELETE FROM ingredients WHERE lower(name) = lower('fresh mint');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint leaves'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint leaves'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('fresh mint leaves'));
DELETE FROM ingredients WHERE lower(name) = lower('fresh mint leaves');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mint leaves'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mint leaves'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mint')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mint leaves'));
DELETE FROM ingredients WHERE lower(name) = lower('mint leaves');

-- Merge group: Mustard powder
UPDATE OR IGNORE ingredients SET name = 'Mustard powder' WHERE lower(name) = lower('raw mustard powder') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Mustard powder'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw mustard powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw mustard powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw mustard powder'));
DELETE FROM ingredients WHERE lower(name) = lower('raw mustard powder');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mustard seed powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mustard seed powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Mustard powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('mustard seed powder'));
DELETE FROM ingredients WHERE lower(name) = lower('mustard seed powder');

-- Merge group: Nutmeg
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg (whole)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg (whole)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Nutmeg (whole)'));
DELETE FROM ingredients WHERE lower(name) = lower('Nutmeg (whole)');

-- Merge group: Okra
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra (bhindi)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra (bhindi)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Okra (bhindi)'));
DELETE FROM ingredients WHERE lower(name) = lower('Okra (bhindi)');

-- Merge group: Onion
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Onion')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('yellow onion'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Onion')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('yellow onion'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Onion')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('yellow onion'));
DELETE FROM ingredients WHERE lower(name) = lower('yellow onion');

-- Merge group: Panch phoran
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Panch phoran')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('panch phoron'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Panch phoran')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('panch phoron'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Panch phoran')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('panch phoron'));
DELETE FROM ingredients WHERE lower(name) = lower('panch phoron');

-- Merge group: Plantain
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green plantain'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green plantain'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('green plantain'));
DELETE FROM ingredients WHERE lower(name) = lower('green plantain');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green plantains'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green plantains'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Plantain')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Green plantains'));
DELETE FROM ingredients WHERE lower(name) = lower('Green plantains');

-- Merge group: Potatoes
UPDATE OR IGNORE ingredients SET name = 'Potatoes' WHERE lower(name) = lower('Potato') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Potatoes'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potato'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potato'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Potato'));
DELETE FROM ingredients WHERE lower(name) = lower('Potato');

-- Merge group: Radish
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radish')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radishes'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radish')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radishes'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radish')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Radishes'));
DELETE FROM ingredients WHERE lower(name) = lower('Radishes');

-- Merge group: Raisins
UPDATE OR IGNORE ingredients SET name = 'Raisins' WHERE lower(name) = lower('Raisin') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Raisins'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisins')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisin'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisins')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisin'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisins')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Raisin'));
DELETE FROM ingredients WHERE lower(name) = lower('Raisin');

-- Merge group: Red chili powder
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chili powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chilly powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chili powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chilly powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chili powder')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Red chilly powder'));
DELETE FROM ingredients WHERE lower(name) = lower('Red chilly powder');

-- Merge group: Rolled oats
UPDATE OR IGNORE ingredients SET name = 'Rolled oats' WHERE lower(name) = lower('Organic rolled oats') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Rolled oats'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rolled oats')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Organic rolled oats'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rolled oats')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Organic rolled oats'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rolled oats')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Organic rolled oats'));
DELETE FROM ingredients WHERE lower(name) = lower('Organic rolled oats');

-- Merge group: Saffron
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Saffron')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('saffron strands'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Saffron')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('saffron strands'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Saffron')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('saffron strands'));
DELETE FROM ingredients WHERE lower(name) = lower('saffron strands');

-- Merge group: Sesame oil
UPDATE OR IGNORE ingredients SET name = 'Sesame oil' WHERE lower(name) = lower('Sesame (Gingelly) Oil') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Sesame oil'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame oil')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame (Gingelly) Oil'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame oil')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame (Gingelly) Oil'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame oil')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sesame (Gingelly) Oil'));
DELETE FROM ingredients WHERE lower(name) = lower('Sesame (Gingelly) Oil');

-- Merge group: Sona Masoori Rice
UPDATE OR IGNORE ingredients SET name = 'Sona Masoori Rice' WHERE lower(name) = lower('Rice (Sona Masoori)') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Sona Masoori Rice'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sona Masoori Rice')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rice (Sona Masoori)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sona Masoori Rice')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rice (Sona Masoori)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sona Masoori Rice')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Rice (Sona Masoori)'));
DELETE FROM ingredients WHERE lower(name) = lower('Rice (Sona Masoori)');

-- Merge group: Sooji
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sooji')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cream of Wheat (sooji)'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sooji')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cream of Wheat (sooji)'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Sooji')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Cream of Wheat (sooji)'));
DELETE FROM ingredients WHERE lower(name) = lower('Cream of Wheat (sooji)');

-- Merge group: Tamarind
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tamarind')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw tamarind'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tamarind')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw tamarind'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tamarind')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('raw tamarind'));
DELETE FROM ingredients WHERE lower(name) = lower('raw tamarind');

-- Merge group: Tomatoes
UPDATE OR IGNORE ingredients SET name = 'Tomatoes' WHERE lower(name) = lower('Tomato') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Tomatoes'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomato'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomato'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomato'));
DELETE FROM ingredients WHERE lower(name) = lower('Tomato');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('large tomatoes'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('large tomatoes'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Tomatoes')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('large tomatoes'));
DELETE FROM ingredients WHERE lower(name) = lower('large tomatoes');

-- Merge group: Turmeric
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric Powder'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric Powder'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Turmeric Powder'));
DELETE FROM ingredients WHERE lower(name) = lower('Turmeric Powder');

-- Merge group: Whole green mung
UPDATE OR IGNORE ingredients SET name = 'Whole green mung' WHERE lower(name) = lower('Whole green moong') AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(name) = lower('Whole green mung'));
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green mung')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green moong'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green mung')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green moong'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green mung')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Whole green moong'));
DELETE FROM ingredients WHERE lower(name) = lower('Whole green moong');

-- Merge group: Yellow moong dal
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow moong dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow split moong dal'));
UPDATE shopping_list_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow moong dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow split moong dal'));
UPDATE inventory_items SET ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow moong dal')) WHERE ingredient_id = (SELECT id FROM ingredients WHERE lower(name) = lower('Yellow split moong dal'));
DELETE FROM ingredients WHERE lower(name) = lower('Yellow split moong dal');

COMMIT;
