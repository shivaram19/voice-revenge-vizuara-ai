# Response Variation and Repetition Avoidance in Spoken Dialogue Systems

**Date:** 2026-04-27  
**Scope:** Conversational AI response variation, fallback message diversity, and repetition penalties in task-oriented and spoken dialogue systems.  
**Research Phase:** DFS (Depth-First Technology Deep-Dive)  
**Target Venues:** ACL, SIGDIAL, Interspeech, AAAI, EMNLP, IJCAI  

---

## 1. Why Repeating Identical Fallback Messages Degrades User Experience

### 1.1 Core Empirical Findings

**Bickmore et al. (2010)** — *Applied Artificial Intelligence*  
In a longitudinal randomized controlled trial (N=24) with a relational exercise-coach agent, participants reported significantly higher desire to continue interacting when the agent used variable dialogue structures (5 alternative templates per state) versus identical formulations. Perceived repetitiveness increased over time in the fixed-dialogue condition, and system usage declined correspondingly [^1].

**Bickmore & Schulman (2009)** — *AAMAS*  
In a crossover study, users were significantly more likely to continue conversations with an agent that varied its utterances. However, a counter-intuitive finding emerged: participants actually walked *more* steps in the non-variable condition, suggesting that while repetition harms engagement and likability, it may paradoxically increase behavioral compliance in short term—yet at the cost of long-term adherence [^2].

**Goldberg et al. (2003)** — *EACL/ISCA Workshop*  
In error-correction subdialogs, exact system repeats of reprompts produced significantly higher user frustration than rephrased or partial-repeat prompts. Rephrasing increased the frequency of user rephrasing (79% vs. 69% after exact repeats), which improves ASR recovery. Apologizing also reduced frustration [^3].

**Chen & Li (2005)** — *Interspeech*  
Users of a spoken dialogue system became "irritated and frustrated, either by the system's unchanged boring voice or by the endless repeating of the long sentence." Two subjects explicitly stated they would not use the system again [^4].

### 1.2 Theoretical and Diagnostic Foundations

**Vrajitoru (2006)** — *IEEE Symposium on Computational Intelligence and Games*  
> "Repetition decreases the life-like impression of the system and undermines the credibility of the system."  
Repetition is also the most frequent "intelligence test" performed by first-time users; systems that fail by echoing identical responses lose user respect [^5].

**Dybkjaer, Bernsen & Dybkjaer (1998)** — *International Journal of Human-Computer Studies*  
Their diagnostic evaluation methodology classifies identical repetition of system questions as a **dialogue design error** (violating Special Principle SP3: "Provide same formulation of the same question..."—intended to reduce ambiguity, but when over-applied to repair prompts, it creates interaction loops). Corpus analysis of the Danish Dialogue System showed repeated identical prompts trapping users in circular error spirals [^6].

**Hayes-Roth (2004); Stern (2003)**  
Believability research establishes that "few things are more disruptive to believability than repetition." Humans never perform the same behavior twice identically; therefore, machine repetition rapidly destroys the "illusion of life." Variability must increase with message frequency, recency, and importance [^7].

**Filisko (2006)** — *MIT Ph.D. Thesis*  
Users of spoken dialogue systems are "aggravated by conversational systems that repeatedly hypothesize the same incorrect words." The dialogue manager must recognize misrecognition loops and react appropriately rather than repeating generic fallbacks [^8].

### 1.3 Synthesis: Mechanisms of Harm

| Mechanism | Source | Effect |
|-----------|--------|--------|
| **Credibility erosion** | Vrajitoru (2006) | Life-like impression destroyed |
| **Engagement decay** | Bickmore et al. (2010) | Desire to continue drops over time |
| **Frustration amplification** | Goldberg et al. (2003) | Exact repeats increase frustration vs. rephrasing |
| **Conversational deadlock** | Dybkjaer et al. (1998) | Users trapped in repetitive loops |
| **ASR degradation** | Goldberg et al. (2003) | Users repeat themselves (bad for recognition) rather than rephrase |
| **Behavioral attrition** | Bickmore & Schulman (2009) | Long-term adherence suffers |

---

## 2. Best Practices for Response Variation

### 2.1 Template Pools with Randomized Selection

**Bickmore et al. (2010)** recommends specifying **multiple agent utterances per dialogue state** and randomly selecting at runtime. In their FitTrack system, each state had 5 alternative templates providing immediate surface variation [^1].

**Practical implementation for rule-based systems:**

```python
import random
from collections import deque

class VariationEngine:
    def __init__(self, templates, history_window=3):
        self.templates = templates  # List[str]
        self.history = deque(maxlen=history_window)
        
    def select(self, context_slots=None):
        # Exclude recently used templates
        candidates = [t for t in self.templates if t not in self.history]
        if not candidates:
            candidates = self.templates  # Reset if all excluded
        
        chosen = random.choice(candidates)
        self.history.append(chosen)
        
        # Slot-filling if context provided
        if context_slots:
            chosen = chosen.format(**context_slots)
        return chosen
```

### 2.2 Slot-Filling and Contextual Substitution

**Walker et al. (2002)** — template-based NLG maps semantic symbols to utterance structures, then applies surface realization. Persistent memory items can condition logical branches and fill template slots, providing variation *over time* as user state changes [^9].

**Bickmore et al. (2010)** used this to vary feedback based on user history:  
- "Looks like you met your exercise goal of {steps} steps. Great job!"  
- "Looks like you got your walking in and met your goal of {steps} steps!"  
- "Way to go—you hit {steps} steps today!" [^1]

### 2.3 Entropy-Based and Strategic Selection

**Rieser & Lemon (2010, 2011)** — *ACL / Springer Monograph*  
Reinforcement learning for adaptive NLG optimizes surface realization jointly with content selection. The policy learns when to summarize, contrast, or recommend based on user preferences and database hit counts—essentially choosing the *information structure* that maximizes expected reward under uncertainty [^10][^11].

For rule-based systems without RL, we can approximate this with **entropy-based template selection**:

```python
import math
from collections import Counter

class EntropySelector:
    def __init__(self, templates):
        self.templates = templates
        self.usage_counts = Counter()
        
    def entropy_weighted_select(self):
        total = sum(self.usage_counts[t] + 1 for t in self.templates)
        # Higher probability for less-used templates
        weights = [1 - (self.usage_counts[t] + 1)/total for t in self.templates]
        chosen = random.choices(self.templates, weights=weights, k=1)[0]
        self.usage_counts[chosen] += 1
        return chosen
```

### 2.4 Dialogue History Filtering

**Treumuth (2008)** and **Vrajitoru (2006)** explicitly recommend checking chat history before emitting a response. If the planned reply exists in recent history [^5][^12]:

1. **Silence/skip** (if non-critical)
2. **Substitute** another template from the pool
3. **Rephrase** using synonymous constructions
4. **Meta-reference** ("As I mentioned earlier...")

### 2.5 Stratified Variation by Intent Type

Not all intents require equal variation. **Dybkjaer et al. (1998)** suggest that task-critical confirmations (SP3) should remain consistent to avoid ambiguity, while social utterances and error recovery should vary maximally [^6].

| Intent Category | Variation Strategy | Rationale |
|-----------------|-------------------|-----------|
| **Critical confirmations** | Fixed formulation | Avoid ambiguity in task-critical information |
| **Error recovery / fallback** | Maximum variation | Minimize frustration and loop detection |
| **Greetings / closings** | High variation | First/last impression management |
| **Task progress updates** | Medium variation + slot-filling | Maintain coherence while avoiding monotony |

---

## 3. Peer-Reviewed Papers on Response Diversity and Repetition Penalty

### 3.1 Diversity-Promoting Objectives in Neural Dialogue

**Li et al. (2016a)** — *NAACL-HLT*  
Proposed **Maximum Mutual Information (MMI)** as a decoding objective to replace MAP estimation:

```
Ŷ = argmax_Y { log p(Y|X) − λ log p(Y) + γ|Y| }
```

The `−λ log p(Y)` term penalizes generic high-probability responses, while `γ|Y|` encourages longer, more informative utterances. This remains the canonical baseline for diversity in neural response generation [^13].

**Li et al. (2016b)** — *ACL*  
Introduced reinforcement learning for dialogue generation with an auxiliary reward for informativeness. The paper identified the "self-repeating problem" in seq2seq models and suggested entropy-maximizing methods (confidence penalty, label smoothing) as mitigations [^14].

**Zhang et al. (2018)** — *NeurIPS*  
**Adversarial Information Maximization (AIM)** jointly optimizes:
1. **Diversity** via adversarial training that matches synthetic and real response distributions
2. **Informativeness** via a variational lower bound on mutual information between query and response [^15].

**Zhao et al. (2017)** — *ACL*  
**Conditional Variational Autoencoders (CVAE)** for discourse-level diversity. A latent variable conditions the decoder, allowing explicit control over response style while maintaining semantic fidelity to the dialogue act. Distinct-1/2 metrics improved significantly over MMI baselines [^16].

### 3.2 Repetition Penalties in Task-Oriented Dialogue Policy

**Zhao et al. (2021)** — *AAAI*  
**Automatic Curriculum Learning with Over-Repetition Penalty (ACL-DQN).** In task-oriented dialogue policy learning, a teacher model samples user goals with a penalty term:

```
Penalty(τ) = λ · (1 − E(τ)/T)
```

Where `E(τ)` is the number of *effective* (non-repeated) answers in trajectory `τ` of length `T`. This guarantees sampled diversity during RL training and significantly improves policy stability [^17].

**Zhang et al. (2018a)** — *IJCAI*  
Reinforcing coherence for seq2seq models in dialogue generation. Introduces a coherence reward that penalizes responses semantically distant from context, which can be combined with diversity objectives to avoid the "dull but diverse" failure mode [^18].

**Xu et al. (2018)** — *EMNLP*  
"Better Conversations by Modeling, Filtering, and Optimizing for Coherence and Diversity." Proposes a two-stage filtering mechanism: generate diverse candidates, then filter for coherence using entailment-based scoring. This prevents the sacrifice of relevance for diversity [^19].

### 3.3 Visual and Multi-Turn Diversity

**Murahari et al. (2019)** — *CVPR* (cited in dialogue literature)  
Explicitly modeled diversity as a constraint in visual dialog using a **repetition penalty** based on smooth-L1 distance between embedding vectors of successive QA pairs. Reduced question repetition from >50% to ~22% [^20].

---

## 4. Practical Recommendations for Rule-Based Intent-Matching Systems

### 4.1 Immediate Implementation (Zero ML)

1. **Template Pool Minimum Size**  
   Maintain ≥3 semantically equivalent but lexically distinct templates for every fallback/non-critical intent. ≥5 for high-frequency intents (greetings, error recovery).

2. **Recent-Exclusion Sampling**  
   Track the last 3 emitted responses per intent category. Never repeat an identical template within the exclusion window. Fall back to the least-recently-used if all are excluded.

3. **Progressive Repair Strategy**  
   Following Goldberg et al. (2003), structure fallback sequences as:
   - **Turn 1:** Apology + rephrased request ("I'm sorry, I didn't catch that. Could you rephrase?")
   - **Turn 2:** Partial acknowledgment + specific guidance ("I heard something about a date—what day did you need?")
   - **Turn 3:** Escalation offer ("Let me transfer you to an agent who can help.")

4. **Slot-Driven Variation**  
   Parameterize templates with user-specific context: `{name}`, `{last_topic}`, `{retry_count}`. Even simple insertion creates perceived personalization.

### 4.2 Intermediate Implementation

5. **Entropy-Weighted Selection**  
   Track template usage frequencies over the session. Weight selection probability inversely to usage count, ensuring uniform coverage.

6. **Intent-Specific Variation Profiles**  
   Use the stratified table (Section 2.5). Apply strict consistency only to legal/health-critical confirmations; maximize variation for social and recovery utterances.

7. **History-Aware Meta-References**  
   If all templates in a pool have been exhausted, switch to explicit acknowledgment:  
   "As I mentioned a moment ago, I can help with scheduling, billing, or general questions. Which would you like?"

### 4.3 Evaluation

8. **Distinct-N Metrics**  
   Compute `Distinct-1/2` (Li et al., 2016a) on logged system utterances per session. Target >0.6 for fallback intents.

9. **Human Evaluation Dimensions**  
   Following Xu et al. (2018), evaluate varied responses on:
   - **Appropriateness** (task correctness)
   - **Interestingness** (engagement)
   - **Non-repetitiveness** (no exact or near-exact repeats within 4 turns)

10. **Loop Detection**  
    Monitor for exact user→system→user echo pairs. If detected twice, force a template from a secondary "break-glass" pool with radically different wording.

---

## References

[^1]: Bickmore, T., Schulman, D., & Yin, L. (2010). Maintaining Engagement in Long-term Interventions with Relational Agents. *Applied Artificial Intelligence*, 24(6), 648–666. https://doi.org/10.1080/08839514.2010.492259

[^2]: Bickmore, T., & Schulman, D. (2009). A Virtual Laboratory for Studying Long-term Relationships between Humans and Virtual Agents. *Proceedings of the 8th International Conference on Autonomous Agents and Multiagent Systems (AAMAS)*, 297–304.

[^3]: Goldberg, J., & Weng, F. (2003). The Impact of Response Wording in Error Correction Subdialogs. *EACL Workshop on Dialogue Systems: Interaction, Adaptation and Styles of Management* / ISCA Workshop. https://www.isca-archive.org/ehsd_2003/goldberg03_ehsd.pdf

[^4]: Chen, F., & Li, S. (2005). Personal Experience with a Spoken Dialogue System. *Interspeech 2005*. https://www.isca-archive.org/interspeech_2005/chen05f_interspeech.pdf

[^5]: Vrajitoru, D. (2006). NPCs and Chatterbots with Personality and Emotional Response. *2006 IEEE Symposium on Computational Intelligence and Games (CIG)*, 142–147.

[^6]: Dybkjaer, L., Bernsen, N. O., & Dybkjaer, H. (1998). A Methodology for Diagnostic Evaluation of Spoken Human-Machine Interaction. *International Journal of Human-Computer Studies*, 48(5), 605–625.

[^7]: Hayes-Roth, B. (2004). Agents on Stage: Advancing the State of the Art of AI. In *Interactive Drama, Art and Artificial Intelligence*. Stanford University; Stern, A. (2003). *Creating Emotional Relationships with Virtual Characters*. In *Ritual and Narrative*.

[^8]: Filisko, E. (2006). *Developing Attribute Acquisition Strategies in Spoken Dialogue Systems via User Simulation*. Ph.D. Thesis, MIT.

[^9]: Walker, M. A., Rambow, O., & Rogati, M. (2002). SPoT: A Trainable Sentence Planner. *NAACL 2002*; see also Wen, T.-H., et al. (2015). Semantically Conditioned LSTM-based Natural Language Generation for Spoken Dialogue Systems. *EMNLP 2015*.

[^10]: Rieser, V., & Lemon, O. (2010). Optimising Information Presentation for Spoken Dialogue Systems. *ACL 2010*.

[^11]: Rieser, V., & Lemon, O. (2011). *Reinforcement Learning for Adaptive Dialogue Systems: A Data-Driven Methodology for Dialogue Management and Natural Language Generation*. Springer.

[^12]: Treumuth, M. (2008). *A Framework for Asynchronous Dialogue Systems*. University of Tartu.

[^13]: Li, J., Galley, M., Brockett, C., Gao, J., & Dolan, B. (2016a). A Diversity-Promoting Objective Function for Neural Conversation Models. *NAACL-HLT 2016*.

[^14]: Li, J., Monroe, W., Ritter, A., Galley, M., Gao, J., & Jurafsky, D. (2016b). Deep Reinforcement Learning for Dialogue Generation. *EMNLP 2016*.

[^15]: Zhang, Y., Galley, M., Gao, J., Gan, Z., Li, X., Brockett, C., & Dolan, B. (2018). Generating Informative and Diverse Conversational Responses via Adversarial Information Maximization. *NeurIPS 2018*, 1815–1825.

[^16]: Zhao, T., Zhao, R., & Eskénazi, M. (2017). Learning Discourse-level Diversity for Neural Dialog Models using Conditional Variational Autoencoders. *ACL 2017*, 654–664.

[^17]: Zhao, Y., Wang, Z., & Huang, Z. (2021). Automatic Curriculum Learning with Over-Repetition Penalty for Dialogue Policy Learning. *AAAI 2021*, 35(16), 14540–14548. https://doi.org/10.1609/aaai.v35i16.17709

[^18]: Zhang, H., Lan, Y., Guo, J., Xu, J., & Cheng, X. (2018). Reinforcing Coherence for Sequence to Sequence Model in Dialogue Generation. *IJCAI 2018*, 4567–4573.

[^19]: Xu, X., Dušek, O., Konstas, I., & Rieser, V. (2018). Better Conversations by Modeling, Filtering, and Optimizing for Coherence and Diversity. *EMNLP 2018*, 3981–3991.

[^20]: Murahari, V., et al. (2019). Learning to Ask Diverse Questions: A Visual Dialog Agent with a Global-Local Perception and Multi-Head Attention Network. *CVPR 2019*; see also VisDial-Diversity framework.
