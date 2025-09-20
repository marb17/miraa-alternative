import spacy
import llmjptoen

# Load GiNZA BERT large
nlp = spacy.load("ja_ginza_bert_large")

text = "なんて私分からなくてさ。"

# Parse the sentence
with nlp.select_pipes(enable=["parser", "tagger", "transformer"]):
    doc = nlp(text)

# Tokenization
tokens = []
for token in doc:
    tokens.append([token.text, token.pos_, token.dep_])

llmjptoen.create_model()
print(str(llmjptoen.batch_explain_tokens(tokens)[0]))