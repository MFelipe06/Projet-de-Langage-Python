# Ardilla : spécification et choix de conception

Projet fil rouge : un langage de programmation et son compilateur vers Python, écrit à la main.

| | |
|---|---|
| **Nom** | Ardilla |
| **Extension** | `.ard` |
| **Paquet Python** | `ardilla` |
| **Commande** | `python -m ardilla run programa.ard` |
| **Paradigme** | impératif, typage dynamique |
| **Syntaxe** | famille du C : accolades et `;` |
| **Mots-clés** | en espagnol |

Chaîne de compilation : `texte .ard → lexer → tokens → parser → AST → analyse sémantique → génération de Python → exécution`.

---

## 1. Les choix de conception et leurs raisons

| # | Choix | Pourquoi |
|---|---|---|
| 1 | **Petit langage cohérent** | Une chaîne complète qui fonctionne vaut mieux qu'un grand langage à moitié implémenté. Les extensions viennent après. |
| 2 | **Accolades `{ }` et `;`** | Les blocs sont délimités sans ambiguïté. Le parser est plus simple et la récupération d'erreurs de l'étape 6 se fait facilement (on se resynchronise sur `;` ou `}`). |
| 3 | **Pas d'indentation significative** | Le lexer n'a pas à produire de tokens `INDENT` / `DEDENT`, source d'erreurs pour un premier compilateur. |
| 4 | **Mots-clés en espagnol** | Donne une identité au langage et le distingue de Python et de la démo Brindille. |
| 5 | **Entiers uniquement, pas de flottants** | Évite l'ambiguïté entre `0..5` (intervalle) et un nombre à virgule, et garde le lexer simple. |
| 6 | **Typage dynamique** | Pas de vérificateur de types à écrire pour l'instant. Le typage statique est l'extension 12. |
| 7 | **Division `/` entière** (traduite en `//`) | Un entier divisé par un entier reste un entier, ce qui est cohérent avec « entiers uniquement ». Attention : `//` arrondit vers le bas, donc `-7 / 2` donne `-4`. |
| 8 | **Comparaisons non chaînables** | `a < b < c` est une erreur de syntaxe. Plus simple et plus sûr qu'une règle implicite. |
| 9 | **Opérateurs logiques en mots** (`y`, `o`, `no`) | Cohérent avec les mots-clés espagnols. Traduits en `and`, `or`, `not`. |
| 10 | **Borne droite de `para` exclue** | Même convention que `range` en Python : `0..6` donne 0 à 5. La traduction est directe. |
| 11 | **Blocs obligatoires** | Même pour une seule instruction : pas d'ambiguïté de type « else pendant ». |
| 12 | **Fonctions globales uniquement** | Simplifie l'analyse sémantique et la génération. La récursion reste autorisée. |
| 13 | **Portée lexicale par bloc** | Règle simple à implémenter avec une pile de portées à l'étape 7. |
| 14 | **Erreur « token manquant » signalée après le dernier token lu** | Plus utile pour l'utilisateur que de pointer le token suivant. |
| 15 | **Exemples avec sortie attendue écrits avant le compilateur** | Ils servent de test d'intégration à l'étape 8. |

---

## 2. Grammaire lexicale

Le lexer ignore espaces, retours à la ligne et commentaires.

### Mots-clés

| Mot-clé | Rôle | Équivalent Python |
|---|---|---|
| `var` | déclarer une variable | affectation |
| `funcion` | déclarer une fonction | `def` |
| `devolver` | retourner une valeur | `return` |
| `si` / `sino` | condition | `if` / `else`, `elif` |
| `mientras` | boucle tant que | `while` |
| `para` / `en` | boucle sur un intervalle | `for ... in range(...)` |
| `mostrar` | afficher | `print` |
| `y` / `o` / `no` | opérateurs logiques | `and` / `or` / `not` |
| `verdadero` / `falso` | booléens | `True` / `False` |

Un mot-clé ne peut pas servir d'identifiant.

### Autres tokens

- **Identifiant** : une lettre ou `_`, puis lettres, chiffres ou `_`.
- **Entier** : suite de chiffres. Le signe n'est pas dans le token : `-5` est l'opérateur `-` appliqué à `5`.
- **Chaîne** : texte entre guillemets doubles, avec les échappements `\n`, `\"`, `\\`.
- **Opérateurs** : `+ - * / %`, `== != < <= > >=`, `=`, `..`
- **Ponctuation** : `( ) { } , ;`
- **Commentaire** : `//` jusqu'à la fin de la ligne.

Point d'attention : le lexer doit lire `<=`, `==`, `!=`, `>=` et `..` comme des tokens uniques.

---

## 3. Types

| Type | Exemples |
|---|---|
| Entier | `0`, `42` |
| Chaîne | `"hola"` (concaténation avec `+`) |
| Booléen | `verdadero`, `falso` |

---

## 4. Instructions

| Instruction | Syntaxe | Traduction Python |
|---|---|---|
| Déclaration | `var x = 5;` | `x = 5` |
| Affectation | `x = x + 1;` | `x = x + 1` |
| Condition | `si c { } sino si d { } sino { }` | `if / elif / else` |
| Tant que | `mientras c { }` | `while c:` |
| Intervalle | `para k en 0..6 { }` | `for k in range(0, 6):` |
| Retour | `devolver e;` ou `devolver;` | `return e` |
| Affichage | `mostrar a, b;` | `print(a, b)` |
| Expression seule | `f(3);` | `f(3)` |
| Fonction | `funcion f(a, b) { }` | `def f(a, b):` |

Les bornes de `para` sont évaluées une seule fois, avant la boucle. Les conditions de `si` et `mientras` n'ont pas besoin de parenthèses.

---

## 5. Expressions : priorité des opérateurs

Du plus faible au plus fort :

| Niveau | Opérateurs | Associativité |
|---|---|---|
| 1 | `o` | gauche |
| 2 | `y` | gauche |
| 3 | `no` (préfixe) | droite |
| 4 | `==` `!=` `<` `<=` `>` `>=` | non chaînable |
| 5 | `+` `-` | gauche |
| 6 | `*` `/` `%` | gauche |
| 7 | `-` (unaire) | droite |
| 8 | appel `f(...)` | gauche |

Les parenthèses regroupent une expression.

---

## 6. Règles sémantiques (vérifiées à l'étape 7)

1. Une variable déclarée avec `var` existe jusqu'à la fin de son bloc.
2. Utiliser ou affecter une variable non déclarée est une erreur.
3. Redéclarer une variable dans le même bloc est une erreur.
4. Dans `para k en ...`, `k` n'existe que dans le corps de la boucle.
5. Les fonctions se déclarent uniquement au niveau global.
6. Appeler une fonction inexistante, ou avec un mauvais nombre d'arguments, est une erreur.
7. `devolver` n'est autorisé que dans une fonction.

L'analyse sémantique collecte les erreurs de noms et de portée, puis les lève
ensemble dans une `SemanticErrors`. Les déclarations de fonctions sont
enregistrées avant l'analyse des instructions, ce qui autorise les appels
récursifs et les appels vers une fonction déclarée plus loin dans le fichier.

---

## 7. Grammaire EBNF

Notation : `{ x }` répétition, `[ x ]` optionnel, `( a | b )` choix, `"mot"` terminal.

```ebnf
(* ---------- Grammaire lexicale ---------- *)
IDENT    = letra { letra | digito | "_" } ;   (* sauf mots-clés *)
ENTERO   = digito { digito } ;
CADENA   = '"' { caracter_normal | escape } '"' ;
escape   = "\n" | "\"" | "\\" ;
letra    = "a".."z" | "A".."Z" | "_" ;
digito   = "0".."9" ;

(* ---------- Grammaire syntaxique ---------- *)
programa      = { funcion | instruccion } ;

funcion       = "funcion" IDENT "(" [ parametros ] ")" bloque ;
parametros    = IDENT { "," IDENT } ;
bloque        = "{" { instruccion } "}" ;

instruccion   = declaracion | asignacion | si | mientras | para
              | devolver | mostrar | expr_instr ;

declaracion   = "var" IDENT "=" expresion ";" ;
asignacion    = IDENT "=" expresion ";" ;
si            = "si" expresion bloque [ "sino" ( si | bloque ) ] ;
mientras      = "mientras" expresion bloque ;
para          = "para" IDENT "en" expresion ".." expresion bloque ;
devolver      = "devolver" [ expresion ] ";" ;
mostrar       = "mostrar" [ expresion { "," expresion } ] ";" ;
expr_instr    = expresion ";" ;

expresion     = disyuncion ;
disyuncion    = conjuncion { "o" conjuncion } ;
conjuncion    = negacion { "y" negacion } ;
negacion      = "no" negacion | comparacion ;
comparacion   = suma [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" ) suma ] ;
suma          = termino { ( "+" | "-" ) termino } ;
termino       = unario { ( "*" | "/" | "%" ) unario } ;
unario        = "-" unario | llamada ;
llamada       = primario { "(" [ argumentos ] ")" } ;
argumentos    = expresion { "," expresion } ;
primario      = ENTERO | CADENA | "verdadero" | "falso" | IDENT
              | "(" expresion ")" ;
```

**Lecture.** Chaque niveau de priorité est une règle qui appelle le niveau suivant, ce qui garantit que `1 + 2 * 3` se lit `1 + (2 * 3)`. Ces niveaux deviendront les puissances de liaison du parser de Pratt à l'étape 5.

**Pourquoi des répétitions `{ }` plutôt que `suma = suma "+" termino` ?** Une règle récursive à gauche ferait boucler un parser descendant.

---

## 8. Programmes d'exemple valides

Chaque `.ard` a un fichier `.out` avec la sortie attendue.

### `ejemplos/factorial.ard`

```
funcion factorial(n) {
    si n <= 1 {
        devolver 1;
    }
    devolver n * factorial(n - 1);
}

para k en 0..6 {
    mostrar k, factorial(k);
}
```

Sortie (`factorial.out`) :

```
0 1
1 1
2 2
3 6
4 24
5 120
```

### `ejemplos/fizzbuzz.ard`

```
funcion clasificar(n) {
    si n % 15 == 0 {
        devolver "FizzBuzz";
    } sino si n % 3 == 0 {
        devolver "Fizz";
    } sino si n % 5 == 0 {
        devolver "Buzz";
    } sino {
        devolver n;
    }
}

para i en 1..16 {
    mostrar clasificar(i);
}
```

Sortie, un élément par ligne : `1`, `2`, `Fizz`, `4`, `Buzz`, `Fizz`, `7`, `8`, `Fizz`, `Buzz`, `11`, `Fizz`, `13`, `14`, `FizzBuzz`.

### `ejemplos/suma.ard`

```
// Somme des entiers de 1 à 10
var total = 0;
var i = 1;
mientras i <= 10 {
    total = total + i;
    i = i + 1;
}
mostrar "suma:", total;
```

Sortie : `suma: 55`

### Génération Python

L'étape 8 traduit l'AST en Python sans utiliser le module `ast` :

- `verdadero` et `falso` deviennent `True` et `False` ;
- `no`, `y` et `o` deviennent `not`, `and` et `or` ;
- `/` devient `//`, conformément à la division entière du langage ;
- `para` devient une boucle sur `range(debut, fin)`, avec borne droite exclue ;
- les fonctions et les variables reçoivent des noms Python internes ;
- `mostrar` et `para` utilisent explicitement les fonctions intégrées de Python,
  pour éviter les collisions avec des noms Ardilla comme `print` et `range`.

Les noms internes distincts pour chaque déclaration préservent aussi les
portées lexicales d'Ardilla, car les blocs Python `if` et `while` ne créent pas
de portée de variables.

## 9. CLI et REPL

Le paquet se lance depuis la racine du projet :

```bash
python -m ardilla run ejemplos/factorial.ard
python -m ardilla compile ejemplos/factorial.ard
python -m ardilla format ejemplos/factorial.ard
python -m ardilla repl
```

Le REPL accepte un programme sur plusieurs lignes. Une ligne vide ou `:run`
compile et exécute la cellule, qui partage les variables et fonctions des
cellules précédentes. `:help` affiche l'aide, et `:quit` quitte le REPL. Les
erreurs lexicales, syntaxiques et sémantiques d'une cellule ne remplacent pas
l'état déjà compilé.

L'étape 10 ajoute un contrat `Backend` basé sur `Protocol`; `PythonBackend`
est son implémentation par défaut. La fonction de formatage reconstruit un
source Ardilla canonique depuis l'AST. Les commentaires, qui ne sont pas
représentés dans l'AST, ne sont pas conservés.

---

## 9. Erreurs attendues

Chaque erreur porte une position `ligne:colonne` (à partir de 1) et un message clair.
Le parser collecte les erreurs syntaxiques et reprend l'analyse après `;` ou `}`.

| Phase | Détectée par | Programme | Erreur attendue |
|---|---|---|---|
| Lexicale | lexer (étape 3) | `mostrar "hola;` | chaîne non terminée, **1:9** (guillemet ouvrant) |
| Syntaxique | parser (étapes 5 et 6) | `var x = 5` puis ligne suivante `mostrar x;` | `;` attendu, **1:10** (juste après le `5`) |
| Sémantique | analyse (étape 7) | `y = 3;` | variable `y` non déclarée, **1:1** |

---

## 10. Points ouverts

À trancher avec l'enseignant :

- **Division par zéro** : erreur d'exécution Python, ou erreur Ardilla dédiée ?
- **Types mélangés** : `"a" + 1` est-il une erreur sémantique ou d'exécution ?

---

## 11. Évolutions possibles

Hors périmètre pour l'instant : listes et indexation, types déclarés et vérifiés (extension 12), génération via le module `ast` (extension 11), source maps (extension 13).

---

## 12. Ce que je dois savoir défendre à l'oral

1. Pourquoi la grammaire a un niveau par priorité et comment elle évite la récursivité à gauche.
2. Pourquoi les comparaisons ne se chaînent pas et pourquoi `/` est entière.
3. La différence entre erreur lexicale, syntaxique et sémantique, avec un exemple de chaque.
4. Pourquoi les exemples avec sortie attendue sont écrits avant le compilateur.