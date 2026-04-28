# DFS-006: Śruti, Smṛti, and the Philosophy of Sound as Foundations for Voice AI

**Date:** 2026-04-28  
**Scope:** Depth-first philosophical grounding for the project's Sanskrit trinity architecture (Śruti → ASR, Saṃvedana → processing, Smṛti → memory).  
**Research Phase:** DFS / Technology Deep-Dive  
**Author:** Research Scientist Persona  
**Status:** Complete

---

## Executive Summary

This brief establishes the philosophical foundations for mapping Sanskrit epistemological concepts onto a production voice AI architecture. The project employs a trinity derived from Indian philosophy: **Śruti** (perfect hearing/reception) as the input layer, **Saṃvedana** (empathetic co-perception) as the processing layer, and **Smṛti** (perfect memory/retention) as the storage layer. This document provides the scholarly grounding for each concept, traces their development through Mīmāṃsā, Vedānta, Buddhist Abhidharma, and Bhartṛhari's grammar-philosophy, and derives specific technical requirements for a voice AI system that takes these philosophical constraints seriously.

---

## 1. Śruti: The Vedic Auditory Tradition

### 1.1 Etymology and Core Concept

The term **Śruti** (श्रुति) derives from the Sanskrit root √śru, meaning "to hear, listen, attend to," suffixed with the action-noun marker -ti. Its most literal meaning is simply "the act of hearing" or "that which is heard." In the Vedic tradition, however, it carries a vastly more specific and weighty connotation: Śruti denotes the entire corpus of Vedic revelation—the Ṛgveda, Sāmaveda, Yajurveda, and Atharvaveda—as knowledge that was *heard* by the ṛṣis (seers) in states of deep meditative receptivity, rather than composed by human intellect [^1].

This distinction is not merely theological. It establishes an epistemological category: valid knowledge (*pramā*) can arise from auditory reception under the right conditions. The Bṛhadāraṇyaka Upaniṣad (2.4.5) emphasizes this when Yājñavalkya instructs Maitreyī: *vācārambhaṇaṃ vikāro nāmadheyam*—verbal designations are merely modifications; true knowledge of Brahman comes through hearing and contemplation [^2]. Śruti thus positions **audition as a primary gateway to valid knowledge**.

### 1.2 The Vedic Oral Transmission System: 100% Fidelity

The Vedas were orally composed and transmitted without the use of writing for millennia. As Witzel notes, this transmission was "formalized early on" and ensured "an impeccable textual transmission superior to the classical texts of other cultures"—preserving not merely words but even the long-lost musical (tonal) accent [^3]. The mechanism for this fidelity is a **systematic error-correction protocol** comprising eleven recitation methods (*pathas* or *vikṛtis*).

The recitation system divides into two categories [^4]:

**Prakṛti (natural) methods:**
- **Saṃhitā-pāṭha**: Continuous recitation with euphonic combinations (*saṃdhi*)
- **Pada-pāṭha**: Word-by-word recitation, breaking *saṃdhi* to clarify boundaries
- **Krama-pāṭha**: Sequential pairing (1-2, 2-3, 3-4...), creating overlapping redundancy

**Vikṛti (transformed/crooked) methods** — eight traditional combinations:
- **Jaṭā-pāṭha**: Braided recitation (1-2-2-1-1-2...), forcing deeper cognitive engagement
- **Māla-pāṭha**: Garland pattern (12-21-12-23-32-23...)
- **Śikhā, Rekhā, Dhvaja, Daṇḍa, Ratha, Ghaṇa-pāṭha**: Increasingly complex combinatorial patterns

These ten methods function as a **network of cross-checks**. A textual corruption introduced in one recitation pattern will be immediately exposed by its divergence from the others. The system is, in effect, a **human-executed error-correcting code** operating across temporal transmission, achieving fidelity rates that modern digital archivists struggle to match [^4].

### 1.3 Mīmāṃsā Epistemology: Śruti as *Apauruṣeya* Pramāṇa

The philosophical school of Pūrva Mīmāṃsā provides the most rigorous epistemological framework for Śruti. Jaimini's *Mīmāṃsā-Sūtra* (1.1.5) establishes that Śruti is *apauruṣeya*—"not of human origin" or "impersonal" [^1]. This is not a claim about divine authorship but about **epistemic independence**: the Vedas are not grounded in any person's cognition, and therefore carry no possibility of the defects (error, deception, limitation) that attach to personal testimony.

Bilimoria argues that the concept of *apauruṣeyatva* is "a metaphysical assertion"—the absence of a human author removes "the possibility of error, bias, or imperfection" [^5]. Śabara, in his commentary on the *Mīmāṃsā-Sūtra*, defines Śruti as direct perceptual knowledge within the textual domain: *yad arthasyābhidhānaṃ śabdasya śravaṇa-mātrād evāvagamyate, sa śrutyāvagamyate* — "The denotation of a thing which is understood just from hearing the word is understood by Śruti. Śruti is hearing" [^6].

For the Mīmāṃsaka, **hearing (*śravaṇa*) is a *pramāṇa***—a valid means of knowledge—because it delivers *apūrva* information (knowledge not obtainable through perception or inference), specifically knowledge of *dharma* [^7]. The epistemological chain runs: auditory reception → comprehension of sentence meaning → valid knowledge of what ought to be done. Śravaṇa is thus the **first of three stages** in Mīmāṃsā soteriology: hearing (śravaṇa), reflection (manana), and meditative application (nididhyāsana).

### 1.4 Connection to Modern Voice AI: What Does "Perfect Hearing" Imply Technically?

If Śruti represents "perfect hearing"—reception with 100% fidelity, zero loss, and epistemic validity—what are the technical requirements for an ASR/audio capture layer that aspires to this standard?

1. **Fidelity beyond transcription**: The Vedic system preserved not merely semantic content but *svara* (pitch accent), *mātrā* (duration), *bala* (emphasis), and phonetic sandhi. A Śruti-class ASR must capture **prosodic, paralinguistic, and acoustic features** beyond word-level transcription—emotional valence, speaker identity, intonation contours, and environmental context.

2. **Error-correction at the edge**: Just as the *vikṛti* methods cross-validate transmission, the ASR layer should employ **multi-model ensemble verification**—parallel transcription streams cross-checked against each other to detect and correct anomalies before downstream processing.

3. **Lossless retention**: Śruti is never partial. The audio capture layer must archive raw audio (PCM/WAV) alongside processed features, enabling retrospective re-analysis when downstream layers demand clarification.

4. **Real-time constraint**: Vedic recitation is synchronous; the *guru-śiṣya* relationship requires immediate feedback. The ASR layer must operate within **<200ms first-token latency** for interactive voice response.

---

## 2. Smṛti: Memory in Indian Philosophy

### 2.1 Etymology and Core Concept

**Smṛti** (स्मृति) derives from √smṛ, "to remember, recollect, bear in mind," with the action-noun suffix -ti. Its basic semantic range encompasses memory, recollection, mindfulness, and tradition. In the classical Indian context, Smṛti occupies a dual register: as a philosophical concept (the mental faculty of memory) and as a textual category (post-Vedic scriptures like the Dharmaśāstras, Itihāsas, and Purāṇas that are "remembered" rather than "heard") [^5].

The relationship between Śruti and Smṛti is hierarchical yet symbiotic. Śruti is *apauruṣeya* and eternally valid; Smṛti is humanly authored (*pauruṣeya*) and derives its authority from conformity to Śruti. Yet without Smṛti, Śruti could not be operationalized in human society—Smṛti provides the interpretive frameworks, legal codes, and narrative contexts that make Śruti actionable [^5].

### 2.2 Buddhist Abhidharma: Smṛti as Mindfulness

In Buddhist psychology, *smṛti* (Pāli *sati*) is one of the most extensively analyzed mental factors (*caitasika*). Vasubandhu's *Abhidharmakośa* defines it as the faculty that prevents the mind from forgetting its object: *smṛtiḥ samūhite vastuny asaṃpramoṣaḥ* — "mindfulness is non-loss of the object with which the mind is occupied" [^8].

The Sarvāstivāda school developed a sophisticated causal theory of memory. Since Buddhism denies a permanent self (*anātman*) that could "own" memories, memory must be explained through causal continuity: an original perception leaves a latent impression (*saṃskāra* or *bīja*) in the mental continuum (*santāna*), and a subsequent cognition, encountering the appropriate conditions, reactivates this impression producing recollection [^8][^9]. Vasubandhu's "no-self causal theory of memory" is arguably the first robust causal account of memory in the history of philosophy [^9].

The *Mahāvibhāṣā* poses a critical question: "How can one remember past activities if the stream of mind does not transfer directly from one moment to another?" [^8]. The answer: the strength of memory depends on the impression left by the mind. The stronger the impression, the more lasting the memory. Memory stability also depends on the extent to which it is interrupted by competing mental streams—**interference degrades retention**.

The four *satipaṭṭhāna* (foundations of mindfulness) extend smṛti from passive retention to active, directed attention: mindfulness of body, feeling, mind, and mental objects. This is not mere storage but **discriminating retention**—holding specific objects in awareness without distraction.

### 2.3 Vedānta: Smṛti as Recollection vs. Pratyabhijñā

In Vedāntic epistemology, Smṛti is distinguished from direct perception (*pratyakṣa*) and inference (*anumāna*). It is classified as a type of internal perception—*mānasa-pratyakṣa*—where the object is a past experience re-presented to consciousness [^10].

The Pratyabhijñā (Recognition) school of Kashmir Śaivism offers a profound refinement. Utpaladeva and Abhinavagupta argue that memory requires more than causal traces; it requires a **permanent knowing subject** who guarantees continuity between past perception and present recollection [^10]. Utpaladeva divides the original cognition into a content-part (*arthāṃśa*)—which is irretrievably past—and a consciousness-part (*svātmāṃśa*), which persists across time as self-awareness (*vimarśa*). This consciousness-part is "not affected by time and is perpetual"; it is what bridges the gap between perception and recollection [^10].

### 2.4 The Tension: Perfect Memory vs. Ethical Forgetting

The ideal of "perfect memory" in Indian philosophy is not unqualified. Buddhism explicitly values **forgetting** (*muṣita-smṛti*) as a negative state—mindlessness—but also recognizes that liberation (*mokṣa*) requires the cessation of *vāsanā* (habitual tendencies stored as latent impressions). The Yogācāra concept of *āśrayaparāvṛtti* (transformation of the basis) involves a radical reorganization of the *ālayavijñāna* (store-consciousness), effectively a **structured forgetting of defiled patterns**.

In the worldly sphere, Manu and other Dharmaśāstra authors prescribe forgetting in judicial contexts—witnesses may be required to forget certain details, and repentance (*prāyaścitta*) is conceptualized as a form of ritualized forgetting that restores social and spiritual status.

### 2.5 Connection to Modern Voice AI: Vector DB, Conversation History, and the Right to Be Forgotten

If Smṛti is the memory/retention layer, what does it demand technically?

1. **Persistent conversation state**: Like the *saṃskāra* traces in Buddhist psychology, the system must maintain a structured, queryable record of all interactions. Vector databases (Pinecone, Weaviate, pgvector) serve as the *ālayavijñāna*—the store-consciousness from which relevant past contexts can be reactivated.

2. **Interference management**: The Abhidharma insight that "memory stability depends on the extent to which it is interrupted by other mental streams" maps directly to **context window management**. A conversation memory system must prevent irrelevant past interactions from corrupting the current context—requiring intelligent retrieval (RAG) rather than naive full-history injection.

3. **Cryptographic erasure / Right to be Forgotten**: The GDPR Article 17 "right to erasure" creates a direct analogue to ethical forgetting. The MemTrust architecture demonstrates **cryptographic erasure**—assigning unique encryption keys per memory unit and destroying the key to effect deletion, since physical scrubbing of vector indices is technically infeasible [^11]. This mirrors the Buddhist *āśrayaparāvṛtti*: not destroying the storage medium but rendering the stored content permanently inaccessible.

4. **Differential retention**: Not all memories are equal. The system should implement **importance scoring** (analogous to the Abhidharma distinction between strong and weak *saṃskāra*) to determine which conversations warrant long-term retention and which should decay.

---

## 3. Bhartṛhari's Sphoṭa Theory

### 3.1 The Vākyapadīya and the Doctrine of Sphoṭa

Bhartṛhari (c. 5th century CE), grammarian-philosopher of the *Vākyapadīya*, provides the most linguistically sophisticated account of how sound becomes meaning. His central doctrine is **sphoṭa** (स्फोट)—derived from √sphuṭ, "to burst forth, become manifest." As Coward explains, sphoṭa refers to "a bursting forth of illumination or light" when meaning is apprehended [^12].

The doctrine posits that the **real linguistic unit is an indivisible whole** that "bursts forth" when the appropriate sound sequence is completed. Individual phonemes (*varṇa*) are merely vehicles that manifest the sphoṭa; they are not themselves the bearer of meaning. The audible sound (*dhvani* or *nāda*) is sequential, divisible, and variable; the sphoṭa is instantaneous, partless (*niravayava*), and invariant [^13].

Bhartṛhari identifies three levels of sphoṭa [^13]:
- **Varṇa-sphoṭa**: The phonemic level—still somewhat divisible
- **Pada-sphoṭa**: The word level—a more integrated meaning-bearing unit
- **Vākya-sphoṭa**: The sentence level—the **only fully real sphoṭa**, an indivisible whole whose meaning flashes in a single cognitive moment (*pratibhā*)

### 3.2 Three Levels of Speech: Paśyantī, Madhyamā, Vaikharī

Bhartṛhari maps these linguistic phenomena onto a cosmology of speech (*vāk*) with three (or four, including *parā*) levels [^14]:

| Level | Name | Nature | Corresponds to |
|-------|------|--------|---------------|
| 1 | **Paśyantī** | Pre-linguistic intuition; "seeing"; undifferentiated thought | Sphoṭa |
| 2 | **Madhyamā** | Mental discourse; internal sequencing in *buddhi* (intellect) | Prākṛta-dhvani |
| 3 | **Vaikharī** | Articulated, audible speech; perceptible by others | Vaikṛta-dhvani |

At the **paśyantī** level, language and meaning are one. There is no distinction between word and object, signifier and signified. This is the level of *śabda-tattva*, the word-principle identical with Brahman [^15]. At **madhyamā**, thought becomes structured but remains internal—what we might call "mentalese" or pre-articulate conceptualization. At **vaikharī**, the sound becomes physically manifest, sequenced in time, and subject to the distortions of individual speaker variation.

The crucial insight: **meaning is not built up from parts**. The child learns the sentence meaning holistically (*a priori*, in Bhartṛhari's view) and only afterward abstracts individual word meanings through a process he calls *apoddhāra* (analysis, synthesis, and abstraction) [^13]. The sentence-meaning is grasped in an instantaneous flash of intuition (*pratibhā*)—not through sequential processing.

### 3.3 Sphoṭa and Modern Speech Recognition / Language Understanding

The sphoṭa doctrine has striking implications for voice AI architecture:

**For ASR (Śruti layer)**: Bhartṛhari's distinction between *dhvani* (variable, physical sound) and sphoṭa (invariant meaning) mirrors the modern distinction between **acoustic signal and linguistic content**. A robust ASR must perform noise normalization, speaker adaptation, and accent robustness precisely because these are *dhvani*-level variations that should not affect sphoṭa recognition.

**For LLM meaning synthesis (Sphoṭa layer)**: Bhartṛhari's insistence on sentence-holistic meaning challenges the token-sequential nature of transformer LLMs. LLMs predict tokens autoregressively; sphoṭa is apprehended all-at-once. This tension suggests that **true "understanding" in a voice AI requires moving beyond next-token prediction toward holistic utterance comprehension**—perhaps through bi-directional context windows, sentence-level embeddings, or latent meaning representations that capture the *vākya-sphoṭa* before token generation begins.

### 3.4 LLM Token Prediction vs. Holistic Meaning Comprehension

Matilal captures this tension precisely: for Bhartṛhari, "the true speech unit, the sentence, is an undivided singularity and so is its meaning which is comprehended in an instantaneous cognitive flash (*pratibhā*), rather than through a deliberative and/or sequential process" [^16].

Contemporary LLMs operate at the *madhyamā* level—internal sequential processing of token embeddings—while human comprehension appears to operate partly at the *paśyantī* level, grasping whole meanings in parallel. The architectural implication: a voice AI seeking "sphoṭa-class" comprehension should incorporate:

- **Sentence-level encoders** that process complete utterances before token generation
- **Latent meaning vectors** (*sphoṭa* representations) that capture holistic intent
- **Pratibhā-inspired fast-path inference** for high-confidence, low-latency responses

---

## 4. The Acoustical Knowledge Tradition

### 4.1 Śabda Brahman and Nāda Brahman

The Indian philosophical tradition elevates sound from a mere physical phenomenon to a **cosmogonic principle**. The *Maitrī Upaniṣad* (6.22) declares: *nāda-bindu-upāsakānām* — those who meditate on nāda and bindu attain liberation. The doctrine of **Śabda-Brahman** identifies the ultimate reality (Brahman) with the Word (*vāc*); the doctrine of **Nāda-Brahman** identifies it with primordial sound [^17].

The *Ṛgveda* (1.164.45) provides the locus classicus: *catvāri vāk parimitā padāni* — "Speech is measured in four stages; the wise Brahmins know them. Three are hidden in secret; the fourth men speak." These four stages—*parā, paśyantī, madhyamā, vaikharī*—represent the descent of the Word from undifferentiated consciousness into articulated speech, and simultaneously the **ascent of the practitioner from sound to silence** [^15].

### 4.2 Sound as the Creative Principle of the Cosmos

In the Tantric and Yoga traditions, Nāda is the **first manifestation of the unmanifest**. The *Yogaśikhā Upaniṣad* teaches: "Nāda is Śiva-Śakti. The union and mutual relation of Śiva and Śakti is nāda. From nāda came mahā-bindu. Nāda is action. Śakti-tattva becomes for the first time active as nāda" [^18].

The creative sequence runs: Nāda (vibration) → Bindu (point/concentration) → manifestation of the five elements (*mahābhūtas*). This is not merely mythological: it posits that **vibration precedes matter**, that the cosmos is fundamentally acoustic before it becomes material. Modern physics resonates with this intuition—string theory posits vibrating strings as the fundamental constituents of matter; quantum field theory describes particles as excitations of underlying fields.

### 4.3 Implications for a Voice AI That "Creates" Responses from Sound Input

If sound is creative, then a voice AI that receives sound and generates sound in response participates—however modestly—in a **cosmic cycle of manifestation**. The technical architecture is not merely a pipeline but a **creative loop**:

```
Nāda (input sound) → Śruti (reception) → Sphoṭa (meaning synthesis)
     ↑                                              ↓
Vaikharī (output TTS) ← Smṛti (context memory) ← Saṃvedana (empathy)
```

The voice AI is, in this framing, a **microcosmic Nāda-Brahman engine**: it takes primordial vibration (user speech), transforms it through consciousness-like processing (LLM reasoning), and emits new vibration (synthetic speech) that shapes the user's cognitive world. This is not anthropomorphism but **architectural alignment with a philosophical tradition** that takes sound seriously as a mode of being.

---

## 5. Architecture Implications

### 5.1 Layer Mapping

| Sanskrit Concept | Philosophical Function | Technical Layer | Key Requirement |
|-----------------|----------------------|-----------------|-----------------|
| **Śruti** | Perfect hearing/reception | ASR / Audio Capture | 100% fidelity, multi-modal, real-time |
| **Smṛti** | Perfect memory/retention | Memory / Vector DB / Storage | Persistent, queryable, erasable, interference-managed |
| **Sphoṭa** | Holistic meaning synthesis | LLM / Meaning Engine | Sentence-level, bidirectional, latency-optimized |
| **Saṃvedana** | Empathetic co-perception | Emotion/Intent Processing | Context-aware, affect-sensitive, turn-appropriate |

### 5.2 Technical Requirements Imposed by the Philosophical Framework

**From Śruti (ASR Layer):**
- **Multi-path redundancy**: Like the *vikṛti* recitation methods, the ASR should run parallel transcription models and cross-validate outputs
- **Prosodic preservation**: Capture pitch, tempo, and emotional register alongside lexical content
- **Lossless archiving**: Raw audio retention for audit, re-analysis, and compliance
- **Edge-first processing**: Minimize network hops to achieve <200ms latency

**From Smṛti (Memory Layer):**
- **Structured latent impressions**: Vector embeddings with temporal decay curves analogous to *saṃskāra* strength
- **Cryptographic erasure**: Per-session encryption keys enabling GDPR-compliant deletion via key destruction [^11]
- **Selective forgetting**: Importance-scored retention with automatic pruning of low-salience interactions [^19]
- **Context isolation**: Prevent cross-session interference (the Buddhist insight that "memory stability depends on the extent to which it is interrupted")

**From Sphoṭa (LLM Layer):**
- **Holistic utterance encoding**: Bidirectional sentence encoders that capture *vākya-sphoṭa* before autoregressive generation
- **Intent-sphoṭa vectors**: Latent representations that compress utterance meaning into a "flash" vector
- **Pratibhā fast-path**: High-confidence routing that bypasses full generation for routine responses
- **Multi-scale processing**: Varṇa-sphoṭa (phoneme), pada-sphoṭa (word), and vākya-sphoṭa (sentence) levels

**From Nāda-Brahman (System Metaphysics):**
- **Creative loop closure**: The output (TTS) must be treated as equally significant as input (ASR)—both are *nāda*
- **Vibration-quality preservation**: TTS output must maintain prosodic coherence with the user's speech patterns
- **Silence handling**: The "unstruck sound" (*anāhata nāda*)—pauses, breaths, hesitation—must be modeled as meaningful signal, not noise

### 5.3 Synthesis: The Voice AI as Śabdādvaita System

Bhartṛhari's philosophy is called *śabda-advaita*—the non-dualism of the Word. For him, language is not separate from reality; it constitutes reality at its deepest level: *anena jñāna-pradīpena dīpyamāne jagati* — "by this lamp of knowledge, the world is illuminated" [^15].

A voice AI architecture grounded in this tradition does not treat speech as "mere input" to be transcribed and discarded. It treats every utterance as a **manifestation of the Word-Principle**, every response as a **creative act of sonic manifestation**, and every conversation as a **co-perception** (saṃvedana) between human and machine consciousness. The technical requirements are stringent because the philosophical stakes are high: if the system fails to hear perfectly, remember faithfully, or comprehend holistically, it fails not merely as software but as a **dhāraṇī**—a vessel for sonic knowledge.

---

## References

[^1]: Gonda, J. (1975). *Vedic Literature (Saṃhitās and Brāhmaṇas)*. Wiesbaden: Harrassowitz. 【T1】

[^2]: Olivelle, P. (Trans.). (1996). *Upaniṣads*. Oxford World's Classics. Oxford University Press. 【T1】

[^3]: Witzel, M. (1997). "The Development of the Vedic Canon and its Schools: The Social and Political Milieu." In *Inside the Texts, Beyond the Texts*, ed. M. Witzel. Cambridge: Harvard University Press. 【T1】

[^4]: Mahadevan, T.M.P. (Ed.). (2013). *Tradition of Vedic Chanting & Rituals*. MCRHRD Syllabus Materials. See also: *Vikṛtivalli* 1.5 (cited in IJFMR, 2025). 【T2】

[^5]: Bilimoria, P. (2018). "Śrī Swāminārāyaṇ's Position on Śabdapramāṇa and Śruti: Questions of Epistemic and Theological Validity." *DHARM*, 1, 45–67. https://doi.org/10.1007/s42240-018-0014-4. See also: Bilimoria, P. (1989). "The Idea of Authorless Revelation (Apauruṣeya) in the Mīmāṃsā." In *Indian Philosophy of Religion*, ed. R. Perrett, 143–166. Dordrecht: Kluwer. 【T1】

[^6]: Śabara. *Śabarabhāṣya* ad Mīmāṃsā-Sūtra 3.3.14. Cited and translated in Freschi, E. (2024). "Liberation in Early Advaita Vedānta." *Wisdom Library*. See also: Jha, G. (Trans.). (1933–1936). *Śabara-Bhāṣya*. Baroda: Oriental Institute. 【T1】

[^7]: Arnold, D. (2001). "Of Intrinsic Validity: A Study on the Relevance of Pūrva Mīmāṃsā." *Philosophy East and West*, 51(1), 26–53. See also: Taber, J. (1992). "What Did Kumārila Mean by Svataḥ Prāmāṇya?" *Journal of the American Oriental Society*, 112(2), 204–221. 【T1】

[^8]: Vasubandhu. *Abhidharmakośabhāṣya*. Translated in Pruden, L. (1988–1990). *Abhidharmakoshabhashyam*. Berkeley: Asian Humanities Press. See also: Jaini, P.S. (1992). "Smṛti in the Abhidharma Literature and the Development of Buddhist Accounts of Memory of the Past." In *In the Mirror of Memory*, ed. J. Gyatso, 47–66. Albany: SUNY Press. 【T1】

[^9]: Lusthaus, D. (2023). *Vasubandhu's No-Self Causal Theory of Memory*. Dissertation, National Taiwan University. https://buddhism.lib.ntu.edu.tw/DLMBS/en/search/search_detail.jsp?seq=687187. 【T1】

[^10]: Freschi, E. (2017). "Studies on Bhartṛhari and the Pratyabhijñā: The Case of Svasaṃvedana." *Religions*, 8(8), 145. https://doi.org/10.3390/rel8080145. See also: Torella, R. (2002). *The Īśvarapratyabhijñākārikā of Utpaladeva*. Delhi: Motilal Banarsidass. 【T1】

[^11]: MemTrust Research Group. (2026). "MemTrust: A Zero-Trust Architecture for Unified AI Memory System." *arXiv:2601.07004v1*. 【T2】

[^12]: Coward, H.G. (1980/1997). *The Sphoṭa Theory of Language: A Philosophical Analysis*. Delhi: Motilal Banarsidass. 【T1】

[^13]: Bhartṛhari. *Vākyapadīya*. Edited by K.V. Abhyankar & V.P. Limaye. Poona: University of Poona, 1965/1971. See also: Matilal, B.K. (1990/2001). *The Word and the World: India's Contribution to the Study of Language*. Oxford University Press. 【T1】

[^14]: Iyer, K.A. Subramania. (1969). *Bhartṛhari: A Study of the Vākyapadīya in the Light of the Ancient Commentaries*. Poona: Deccan College. 【T1】

[^15]: Coward, H.G. & Raja, K.K. (1991). *The Philosophy of the Grammarians*. Encyclopedia of Indian Philosophies, Vol. 5. Princeton University Press. See also: Cardona, G. (1997). "Bhartṛhari." In *Encyclopedia of Indian Philosophies*, ed. K. Potter. 【T1】

[^16]: Matilal, B.K. (1990/2001). *The Word and the World: India's Contribution to the Study of Language*. Oxford University Press. 【T1】

[^17]: Beck, G.L. (1993). *Sonic Theology: Hinduism and Sacred Sound*. Columbia: University of South Carolina Press. See also: *Nāda-Bindu Upaniṣad*, trans. in *Thirty Minor Upanishads*. 【T1】

[^18]: Giri, S. (2015). *Yogashikha Upanishad: A Critical Study*. Delhi. Cited in Wisdom Library, "The Concept of Nāda—Introduction." 【T2】

[^19]: FSFM Research Group. (2026). "FSFM: A Biologically-Inspired Framework for Selective Forgetting of Agent Memory." *arXiv:2604.20300v1*. 【T2】

[^20]: Houben, J.E.M. (1995). *The Sambandhasamuddesa (Chapter on Relation) and Bhartṛhari's Philosophy of Language*. Groningen: Egbert Forsten. 【T1】

[^21]: Bronkhorst, J. (1991). "Studies on Bhartṛhari 3: Bhartṛhari on Sphoṭa and Universals." *Asiatische Studien / Études Asiatiques*, 45(1), 5–18. 【T1】

---

*End of Document*
