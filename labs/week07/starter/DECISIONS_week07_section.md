# Week 7: a RAG pipeline you can score

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 7

**Run conditions.** embedding model: nomic-embed-text:latest (Ollama,
local) | dimensionality: 768 | chunk size: 600 characters | overlap: 80
| k: 5 | store: Chroma, in memory | date: 2026-10-27 | table from: my
own index

### 1. The chunker

size 600, overlap 80, because these are the course defaults and keeping
them makes my table comparable with the course's; 600 characters is
about one paragraph, so most chunks are about one thing (29 of the 56
sections fit in a single chunk), and 80 characters of overlap mean a
sentence cut at a chunk border appears whole in the next chunk.

Sizes are in characters, not tokens or sentences, so a chunk can end
mid-sentence. Each chunk keeps its doc_id and section, its text starts
with the section heading, and its id is doc_id::section::n. The stride
is 520, so the longest section (RB-ARRIVEE::Who must declare, 1,224
characters) becomes three chunks: 0-600, 520-1120 and 1040-1224.

### 2. The index

95 chunks, 768 dimensions, 2.79 seconds for one full indexing run
(embedding in batches of 32 and adding to Chroma; one run on
2026-10-27, which may include loading the embedding model).

### 3. The table

| qid | dense rank | keyword rank | recall@5 | tags |
| Q01 | 1 | 3 | 1.00 | distractor, superseded |
| Q02 | 1 | 14 | 1.00 | rare-token |
| Q03 | 1 | 1 | 1.00 | easy |
| Q04 | 1 | 1 | 1.00 | vocabulary |
| Q05 | 22 | 17 | 0.00 | multi-document |
| Q06 | 1 | 5 | 1.00 | negation |
| Q07 | 1 | 3 | 1.00 | easy |
| Q08 | 1 | 1 | 1.00 | numeric |
| Q09 | 1 | 2 | 1.00 | distractor |
| Q10 | 1 | 1 | 1.00 | easy |
| Q11 | 1 | 12 | 1.00 | easy |
| Q12 | - | - | - | unanswerable |

recall@5 is the dense retriever's, counted over sections. Dense puts a
gold chunk in the top 5 on 10 of 11 answerable questions. Dense beats
keyword on 6, keyword beats dense on 1 (Q05), and 4 tie at rank 1.

Dense beats keyword by the most on Q02 (1 against 14). The question
carries the code RB-1140b, but in term overlap every word counts one
point, so the code weighs no more than "for" or "have". The gold chunk
matched two words; one chunk shared three ordinary words, twelve shared
two, and the tie rule (alphabetical by chunk_id) put all of them first.
Dense matched the meaning, "I was asked to fill in a form, what is it
for", to the section on how to apply.

### 4. Good pipeline, or easy task?

Ten of eleven at rank 1 is evidence that the task is easy, not that the
pipeline is good: ten short documents on clearly separate topics, and
questions that mostly use the documents' own words; the four ties show
that even crude term overlap ranks those questions first.

What this measurement still cannot tell me: whether a model would
answer correctly from the retrieved chunks, and whether the pipeline
would refuse Q12, because a vector store always returns k chunks, even
when none of them answers the question.

### 5. The question that fails on both

Question: Q05, "I have just moved to Remerbaach and I own a car. What
do I have to do at the commune?". Dense rank 22, keyword rank 17.

Why it fails:

It needs two sections in two documents, RB-ARRIVEE::Deadline and
RB-VIGNETTE::How to apply, but one query becomes one vector, and it
lands between the two needs. Dense's top 5 were RB-ARRIVEE::Who must
declare, RB-TRANSPORT::The communal shuttle, RB-ARRIVEE::(intro),
RB-TRANSPORT::(intro) and RB-HIVER::What the commune clears: the right
arrival document but the wrong section, and "car" pulled towards public
transport, because the question never says parking. Keyword's top
ranks were won by common words such as "and", "the" and "commune".

Would any chunk size fix it? No, because the two answers sit in
different documents and the chunker never crosses a section, so no
chunk of any size can hold both. The limit is the single query, not
the chunk: splitting the question into two queries and merging the
results is the fix to try (not done, see Deferred).

### 6. The gold-set correction

The note said: RB-1140b is "rare, exact, and semantically empty, so
dense retrieval is the wrong tool for it and keyword search is the
right one".

My measurement said: the reverse. Dense ranks the gold section 1,
keyword 14.

The corrected note, now in goldset.py:

"The query carries the string RB-1140b. The original note said a rare
exact token is where dense retrieval loses and keyword search wins.
Measured on 2026-10-27 (nomic-embed-text, chunks of 600 with 80
overlap), it is the reverse: dense ranks the gold section 1, keyword
14. Term overlap counts every term as one point, so the rare token
weighs no more than 'for' or 'have': the gold chunk ties with twelve
chunks that share only common words and loses the tie. A keyword search
that weights rare terms (BM25) was not tested. Note that a superseded
page carries the near-identical string RB-1140a."

It cost one run of 01_retrieve.py and a look at the keyword ranking.
Not finding it would have left a false claim in my gold set, and later
weeks that reload the gold set would have built on it.

### Homework: the chunk sweep

Same gold set and overlap 80, 2026-10-27. Each cell is dense rank /
keyword rank. Results in `artifacts/week07_sweep_s300.json`,
`artifacts/week07_retrieval.json` (600) and
`artifacts/week07_sweep_s1200.json`.

| qid | 300 (187 chunks) | 600 (95 chunks) | 1200 (57 chunks) |
| Q01 | 1 / 4 | 1 / 3 | 1 / 4 |
| Q02 | 1 / 17 | 1 / 14 | 1 / 4 |
| Q03 | 1 / 1 | 1 / 1 | 1 / 2 |
| Q04 | 1 / 1 | 1 / 1 | 1 / 1 |
| Q05 | 37 / 16 | 22 / 17 | 20 / 13 |
| Q06 | 1 / 4 | 1 / 5 | 1 / 1 |
| Q07 | 1 / 2 | 1 / 3 | 1 / 2 |
| Q08 | 1 / 1 | 1 / 1 | 1 / 1 |
| Q09 | 1 / 3 | 1 / 2 | 1 / 4 |
| Q10 | 1 / 1 | 1 / 1 | 1 / 1 |
| Q11 | 1 / 18 | 1 / 12 | 1 / 14 |

Which questions move: on dense, none that matter. Every answerable
question except Q05 stays at rank 1 at every size, and Q05 stays out of
the top 5 (37, 22, 20; part of that movement is only the number of
chunks shrinking), which confirms entry 5: no chunk size fixes it. On
keyword, Q02 moves most, from 17 to 14 to 4: a longer chunk holds more
of the common query words, so the gold chunk catches up with the chunks
that beat it, which suggests term overlap favours long chunks. Q11
(18, 12, 14) does not follow that pattern, so it is not a rule. Q06
rises to rank 1 on keyword at 1200.

I keep 600: dense retrieval, the one I would ship, gives the same ranks
at all three sizes, and 600 keeps each chunk on one topic and the text
a model will later read short. On this corpus, retrieval rank alone is
too easy a test to choose a chunk size.

### Homework: wiring the retriever into the memory store

The brief says to copy the week 7 files into `app/`, wire
`MemoryStore.search`, remove an `@stub` line and prove it with
`python -m app.run`. My repository has no `app/` package, no `app.run`
and no `@stub`: the memory store is `labs/week06/starter/memory.py`. I
followed the week 6 comment instead ("Week 7 replaces the body of this
method with embeddings and the signature does not change"):
`search(subject, query, k)` keeps its signature and still filters to
one subject first, then ranks that subject's facts by cosine similarity
of nomic-embed-text embeddings (the week 7 `embed`) instead of counting
shared words. No chunking: a fact is one short sentence. I did not
point it at the commune corpus, because that would return the same
documents for every resident and make the subject boundary pointless.

Proof, A. Muller's facts, 2026-10-27, query "How do I register a new
address?":

| search | result, in order |
| keyword (before) | Has a 120 litre bin collected weekly |
| dense (after) | Lives at Rue Principale 4, Prefers email only, Has a 120 litre bin collected weekly |

The keyword version returned the bin fact because it shares the word
"a" with the question, and dropped the address fact, which shares no
word. Dense ranks the address first. The cost is the week 7 lesson:
dense always returns k facts, so the two unrelated ones come back too,
only lower. With "email" and k = 1 both versions return "Prefers email
only". The MCP recall tool calls this method, so it now searches by
meaning too; the server now needs `labs/week07/starter` on PYTHONPATH.

### The gold set

`artifacts/goldset.json` now holds 58 cases: the 12 week 7 retrieval
questions were added by 01_retrieve.py, tagged task:retrieval, with Q12
marked must_refuse.

### Deferred

- Stretch: splitting Q05 into two queries, and explaining a question
  where keyword ties dense. Not attempted.
- A keyword search that weights rare terms (BM25) was not tested, so
  entry 6 says only what term overlap does.
- The wired memory search has no similarity threshold, so when a
  resident has fewer relevant facts than k, unrelated ones are
  returned too.