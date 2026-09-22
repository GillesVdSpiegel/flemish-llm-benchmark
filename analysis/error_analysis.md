# Error analysis — A1 lexicon track

Models: chocollama-8b, claude-sonnet-5, eurollm-9b, geitje-7b-ultra, gemma4-12b, gpt-5.6-terra. Items: 788 (public split, first run).


## Items every model gets wrong

1 of 788 items.

- **konijnenpijp** (be): gold *konijnenhol*; all models chose *aanbouwsel, bijgebouwtje*


## Belgian words most models miss (17)

- konijnenpijp (0% of models correct)
- balkleed (17% of models correct)
- bezetsel (17% of models correct)
- solsleutel (17% of models correct)
- roefelen (17% of models correct)
- baancafé (33% of models correct)
- beterhand (33% of models correct)
- afpitsen (33% of models correct)
- klissen (33% of models correct)
- champetter (33% of models correct)
- nieuwkuis (33% of models correct)
- omwringen (33% of models correct)
- postogram (33% of models correct)
- overkop (33% of models correct)
- vadsigaard (33% of models correct)
- vidé (33% of models correct)
- witteke (33% of models correct)


## Netherlands words most models miss (10)

- apezuur (17% of models correct)
- glom (17% of models correct)
- poepdoos (17% of models correct)
- eigenheimer (33% of models correct)
- giebel (33% of models correct)
- gierton (33% of models correct)
- klunen (33% of models correct)
- bul (33% of models correct)
- moetje (33% of models correct)
- staalpil (33% of models correct)


## Accuracy by origin of the gold answer

              mean        count      
variety         be     nl    be    nl
gold_source                          
bulk         0.827  0.845  1788  1776
checked      0.778  0.828   576   588


## Accuracy by how well the word is known in its own country

variety          be     nl
p_bin                     
(0.79, 0.85]  0.759  0.805
(0.85, 0.9]   0.811  0.847
(0.9, 0.95]   0.826  0.844
(0.95, 1.0]   0.886  0.890

_Prevalence bins from the DCP norms (CC BY-NC); aggregate figures only._


## Which distractor is chosen when wrong

distractor_variety   ?   be   nl
variety                         
be                  18  215  205
nl                  12  185  180

_Columns: the variety of the word whose meaning was chosen instead._


## Discordant pairs per model

- chocollama-8b: BE right / NL wrong 86, NL right / BE wrong 65
- claude-sonnet-5: BE right / NL wrong 4, NL right / BE wrong 12
- eurollm-9b: BE right / NL wrong 28, NL right / BE wrong 43
- geitje-7b-ultra: BE right / NL wrong 37, NL right / BE wrong 68
- gemma4-12b: BE right / NL wrong 77, NL right / BE wrong 91
- gpt-5.6-terra: BE right / NL wrong 13, NL right / BE wrong 27
