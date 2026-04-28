# Canonical Bibliography

> *"Standing on the shoulders of giants — but verifying each shoulder's load-bearing capacity first."*

---

## ASR & Speech Recognition

1. **Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I.** (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv:2212.04356*.
   - *Canonical Whisper paper. 680k hours of weak supervision. Encoder-decoder Transformer.*

2. **Baevski, A., Zhou, Y., Mohamed, A., & Auli, M.** (2020). wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations. *NeurIPS*.
   - *Self-supervised pretraining for ASR. 60k hours unlabeled audio.*

3. **Gandhi, S., et al.** (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. *arXiv:2311.00430*.
   - *49% smaller, 5.8× faster, within 1% WER. Hugging Face.*

4. **Gerganov, G.** (2023). whisper.cpp. *GitHub: ggerganov/whisper.cpp*.
   - *C++ port for edge deployment. CPU/GPU/WASM support.*

5. **SYSTRAN.** (2023). faster-whisper. *GitHub: SYSTRAN/faster-whisper*.
   - *CTranslate2 optimization. 4× speedup over original.*

6. **Ardila, R., et al.** (2020). Common Voice: A Massively-Multilingual Speech Corpus. *LREC*.
   - *Open-source multilingual speech dataset for bias evaluation.*

---

## TTS & Speech Synthesis

7. **Kim, J., Kong, J., & Son, J.** (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. *ICML*.
   - *VITS architecture. Basis of Piper TTS.*

8. **Shen, J., et al.** (2018). Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions. *ICASSP*.
   - *Tacotron 2 + WaveNet pipeline.*

9. **Hansen, M.** (2023). Piper: A fast, local neural text-to-speech system. *GitHub: rhasspy/piper*.
   - *7M parameters. Raspberry Pi 4 real-time. ONNX Runtime.*

10. **Coqui AI.** (2023). Coqui TTS. *GitHub: coqui-ai/TTS*.
    - *Toolkit with Tacotron2, FastSpeech2, VITS, YourTTS, XTTS.*

11. **Chevi, et al.** (2023). Nix-TTS: Lightweight neural TTS via knowledge distillation. *Edge GenAI preprint*.
    - *5.23M parameters. RTF 1.97 on Raspberry Pi 3B.*

---

## LLM Reasoning & Tool Use

12. **Yao, S., et al.** (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.
    - *Reasoning + action loop for agentic behavior.*

13. **OpenAI.** (2023). Function Calling API. *Platform Documentation*.
    - *Structured tool use for GPT models.*

14. **Qiu, J., et al.** (2026). VoiceAgentRAG: Solving the RAG Latency Bottleneck in Real-Time Voice Agents. *arXiv:2603.02206*.
    - *Dual-agent memory router. 316× retrieval speedup.*

15. **Lewis, P., et al.** (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*.
    - *Canonical RAG paper.*

---

## Streaming & Real-Time Systems

16. **SigArch.** (2026). Building Enterprise Realtime Voice Agents from Scratch. *arXiv:2603.05413*.
    - *Streaming pipeline architecture. Latency equations.*

17. **LiveKit.** (2026). Pipeline vs. Realtime — Which is the better Voice Agent Architecture? *Blog*.
    - *Comparison table: modularity vs native S2S.*

18. **Gokuljs.** (2026). How Real-Time Voice Agents Work: Architecture and Latency. *Blog*.
    - *Turn gap budgets. WebRTC vs WebSocket.*

19. **Chanl.ai.** (2026). Voice Agent Platform Architecture: The Stack Behind Sub-300ms Responses. *Blog*.
    - *Production architecture with dual real-time + async paths.*

20. **Ethiraj, V., et al.** (2025). Toward Low-Latency End-to-End Voice Agents. *arXiv:2508.04721*.
    - *Streaming ASR + quantized LLMs + real-time TTS.*

---

## Transport & Infrastructure

21. **Fette, I., & Melnikov, A.** (2011). RFC 6455: The WebSocket Protocol. *IETF*.

22. **RFC 8829 / 8830.** WebRTC Standards. *IETF*.

23. **Van Landuyt, D.** (2023). A Comparative Study of WebRTC and WebSocket. *Ghent University Thesis*.
    - *SFU vs MCU analysis. Latency benchmarks.*

24. **Leviathan, Y., Kalman, M., & Matias, Y.** (2023). Fast Inference from Transformers via Speculative Decoding. *ICML*.
    - *2× speedup with assistant model.*

25. **Kwon, W., et al.** (2023). vLLM: Efficient Memory Management for Large Language Model Serving with PagedAttention. *SOSP*.
    - *Continuous batching for LLM serving.*

---

## Distributed Systems & Architecture

26. **Brewer, E.** (2000). Towards Robust Distributed Systems. *PODC*.
    - *CAP theorem.*

27. **Vogels, W.** (2009). Eventually Consistent. *CACM*.

28. **Newman, S.** (2015). *Building Microservices*. O'Reilly.

29. **Beyer, B., et al.** (2016). *Site Reliability Engineering*. O'Reilly.
    - *RED/USE metrics. Distributed tracing.*

30. **Barroso, L. A., Clidaras, J., & Hölzle, U.** (2018). *The Datacenter as a Computer*. Morgan & Claypool.

31. **NVIDIA.** (2023). Autoscaling Riva Deployment with Kubernetes for Speech AI. *Developer Blog*.
    - *HPA with custom metrics. GPU autoscaling.*

---

## VAD & Turn-Taking

32. **Rabiner, L. R., & Sambur, M. R.** (1975). An Algorithm for Determining the Endpoints of Isolated Utterances. *Bell System Technical Journal*.
    - *Classical VAD foundation.*

33. **Silero Team.** (2024). Silero VAD. *GitHub: snakers4/silero-vad*.
    - *LSTM-based. <1ms per chunk on CPU.*

34. **Phoenix-VAD.** (2025). Streaming Semantic Endpoint Detection for Full-Duplex Speech Interaction. *arXiv:2509.20410*.
    - *Semantic VAD using lightweight LLM.*

35. **Clark, H. H.** (1996). *Using Language*. Cambridge.
    - *Action ladder model of dialogue. Turn-taking theory.*

---

## Vector Search & Memory

36. **Johnson, J., Douze, M., & Jégou, H.** (2019). Billion-scale similarity search with GPUs. *IEEE TBD*.
    - *FAISS library.*

37. **Robertson, S., & Zaragoza, H.** (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*.
    - *Classical probabilistic retrieval model.*

38. **ITU-T.** (1972). G.711: Pulse Code Modulation (PCM) of Voice Frequencies.
    - *μ-law/A-law companding. PSTN audio standard.*

39. **Malkov, Y. A., & Yashunin, D. A.** (2016). Hierarchical Navigable Small World graphs. *arXiv:1603.09320*.
    - *HNSW indexing.*

---

## Native Speech-to-Speech Models

40. **Défossez, A., et al.** (2024). Moshi: a speech-text foundation model for real-time dialogue. *Kyutai Technical Report*.
    - *7B dual-stream. ~200ms latency. Rust+CUDA server.*

41. **OpenAI.** (2024). GPT-4o Realtime API. *Platform Documentation*.
    - *Audio-in, audio-out. ~400ms voice-to-voice.*

42. **Cockburn, A.** (2005). Hexagonal Architecture. *alistair.cockburn.us*.
    - *Ports and adapters pattern. Domain-centric design.*

43. **Twilio.** (2024). Media Streams API Documentation. *twilio.com/docs/voice/media-streams*.
    - *WebSocket audio relay for PSTN. 8kHz mulaw.*

44. **Stripe.** (2023). Idempotency Keys API Design. *stripe.com/docs/api/idempotent_requests*.
    - *Prevent duplicate operations under retry.*

45. **Deepgram.** (2023). Best Practices for Voice Activity Detection. *deepgram.com/learn/vad-best-practices*.
    - *300ms silence threshold optimization.*

---

44. Microsoft. (2024). Azure OpenAI Service Documentation. learn.microsoft.com/azure/ai-services/openai/.
45. IETF. (2012). RFC 6716: Definition of the Opus Audio Codec.
46. American Medical Association. (2021). Optimized Scheduling for Primary Care Practices.
47. Microsoft Research. (2022). Semantic + Keyword Hybrid Search for Enterprise Directories.
48. Piper TTS. (2023). github.com/rhasspy/piper.
49. IETF. (2021). RFC 8861: Congestion Control and Packet Size for WebRTC.
50. SciPy. (2023). scipy.signal.resample_poly Documentation. docs.scipy.org.

51. **Keith, et al.** (2024). Text-to-speech on Edge Devices. *SIGUL*.
52. **Sigelman, B. H., et al.** (2010). Dapper, a Large-Scale Distributed Systems Tracing Infrastructure. *Google Technical Report*.
53. **OpenTelemetry.** (2023). OpenTelemetry Specification. *opentelemetry.io*.
54. **Wilkes, J.** (2020). Google-Wide Cluster Scheduling: The Next Generation. *Google SRE Book, Chapter 24*.
55. **Van Landuyt, D.** (2023). SFU vs MCU Analysis. *Ghent University Thesis*.
56. **National Association of Home Builders.** (2024). Cost of Construction Survey.
57. **Occupational Safety and Health Administration.** (2024). Construction Industry Standards.
58. **NVIDIA.** (2024). GPU Operator Troubleshooting. *docs.nvidia.com*.
59. **LiteASR.** (2025). Efficient Automatic Speech Recognition with Low-Rank Approximation. *arXiv:2502.20583*.
60. **Gunawi, H. S., et al.** (2016). Why Does the Cloud Stop Computing? *HotCloud*.
61. **Deepgram.** (2024). Nova-3 Streaming ASR Documentation. *Deepgram Developer Docs*.
62. **Russell, S., & Norvig, P.** (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
63. **Inworld.ai.** (2026). Best GPU Cloud for AI Inference.
64. **Callsphere.tech.** (2026). AI Agent Deployment on Kubernetes.
65. **APSIPA.** (2025). Integrating Faster Whisper with Deep Learning Speaker Recognition.
66. **gRPC Authors.** (2023). gRPC Core Documentation. *grpc.io*.
67. **ResearchGate.** (2024). A Comparative Study of WebRTC and WebSocket Performance in Real-Time Voice Communication.
68. **Skywork.ai.** (2025). OpenAI Realtime API vs WebRTC 2025.
69. **LiveKit.** (2025). LiveKit Agents Framework Documentation.
70. **IWLSDS.** (2025). Analysis of Voice Activity Detection Errors in API-based Dialogue Systems.
71. **WebRTC.org.** (2023). Acoustic Echo Cancellation Documentation.
72. **Deepgram.** (2024). Endpointing Configuration Best Practices.
73. **tderflinger.com.** (2024). Open Source Voice Bot ASR/TTS Guide.
74. **Tezeract.ai.** (2026). ReAct vs Function Calling Agents.

75. **UGent.** (2023). SFU vs MCU Analysis. *Ghent University Thesis*.
76. **arXiv.** (2024). Speech Recognition for Live Transcription and Voice Commands. *arXiv:2410.15608*.
77. **arXiv.** (2025). Whisper Turns Stronger: Augmenting Wav2Vec 2.0 for Superior ASR. *arXiv:2501.00425*.
78. **IWLSDS.** (2025). Analysis of Voice Activity Detection Errors in API-based Dialogue Systems.

79. **Fielding, R. T.** (2000). Architectural Styles and the Design of Network-based Software Architectures. *PhD thesis, University of California, Irvine*.
    - *REST architectural style. Statelessness, cacheability, layered system.*

80. **Twilio.** (2024). Recordings API Documentation. *twilio.com/docs/voice/api/recording*.
    - *Dual-channel recording, callback delivery, secure storage.*

81. **Twilio.** (2024). Privacy and Compliance Guide for Call Recording. *twilio.com/docs/glossary/what-is-call-recording*.
    - *One-party vs all-party consent. PCI-DSS and HIPAA considerations.*

82. **Google.** (2019). Search Engine Optimization (SEO) Starter Guide. *developers.google.com/search/docs/fundamentals/seo-starter-guide*.
    - *Domain structure, path vs subdomain ranking considerations.*

83. **Barth, A.** (2011). RFC 6265: HTTP State Management Mechanism. *IETF*.
    - *Cookie scope, Domain attribute, same-origin policy.*

84. **Fielding, R. T.** (2000). Architectural Styles and the Design of Network-based Software Architectures. *PhD thesis, UC Irvine*.
    - *REST constraints: layered system, cacheability, uniform interface.*

85. **Nielsen, J., & Loranger, H.** (2006). *Prioritizing Web Usability*. New Riders.
    - *Trust and credibility signals in web interfaces.*

86. **Let's Encrypt.** (2024). ACME Protocol Documentation. *letsencrypt.org/docs*.
    - *Automated TLS certificate provisioning.*

87. **Moz.** (2024). Domain SEO Explained. *moz.com/learn/seo/domain*.
    - *Subdomain vs subdirectory ranking implications.*

88. **Wiggins, A.** (2017). The Twelve-Factor App. *12factor.net*.
    - *Config in environment, stateless processes, dev/prod parity.*

89. **OWASP.** (2023). Secrets Management Cheat Sheet. *owasp.org*.
    - *Env vars preferred over hardcoded secrets. Rotation policies.*

*Bibliography compiled: 2026-04-27*
*Total entries: 89*
*Coverage: ASR (6), TTS (5), LLM/Agents (4), Streaming (5), Infrastructure (6), Architecture (6), VAD (4), Memory (3), S2S (2), API Design (3), Telephony Compliance (1), Web UX (1), Security (1)*

---

## Sanskrit Philosophy, Poetics & Epistemology

90. **Bharata Muni.** (c. 2nd c. BCE–2nd c. CE). *Nāṭyaśāstra*. Chapter 6: *Rasādhyāya*.
    - *Foundational text of Indian dramaturgy. The Rasasūtra (6.36): "Vibhāvānubhāva-vyabhicāri-saṃyogād rasa-niṣpattiḥ."*

91. **Abhinavagupta.** (10th–11th c. CE). *Abhinavabhāratī* (commentary on *Nāṭyaśāstra*) and *Locana* (commentary on *Dhvanyāloka*).
    - *Kashmiri Śaiva philosopher who deepened Rasa theory with the concepts of Sahrdaya, Sādhāraṇīkaraṇa, and universalization.*

92. **Bhartṛhari.** (5th c. CE). *Vākyapadīya*. Kāṇḍa I.
    - *Foundational text of Sanskrit philosophy of language. Doctrine of Sphoṭa and three levels of speech: paśyantī, madhyamā, vaikharī.*

93. **Ānandavardhana.** (9th c. CE). *Dhvanyāloka*.
    - *Foundational text of Sanskrit poetics on suggested meaning (dhvani). Commentary by Abhinavagupta (*Locana*).*

94. **Monier-Williams, M.** (1899). *A Sanskrit-English Dictionary*. Clarendon Press, Oxford.
    - *Canonical Sanskrit-English lexicon. s.v. śruti, saṃvedana, smṛti, hṛdaya, sphoṭa, dhvani.*

95. **Macdonell, A. A.** (1893). *A Sanskrit-English Dictionary*. Longmans, Green & Co.
    - *Earlier comprehensive Sanskrit lexicon with etymological notes.*

96. **Uskokov, A.** (University of Chicago). *Deciphering the Hidden Meaning: Scripture and the Hermeneutics of Liberation in Early Advaita Vedānta*. PhD dissertation.
    - *Citing Śabara's Mīmāṃsābhāṣya on Śruti as pramāṇa.*

97. **Van Buitenen, J. A. B.** (1974). *The Mahābhārata: 1. The Book of the Beginning*. University of Chicago Press.
    - *Cited on the tradition of Śruti, Smṛti, and authoritative transmission.*

98. **Holdrege, B. A.** (1996). *Veda and Torah: Transcending the Textuality of Scripture*. State University of New York Press.
    - *Comparative study of Vedic and Jewish scripture traditions, including Śruti oral transmission.*

99. **Muller-Ortega, P. E.** (1989). *The Triadic Heart of Siva: Kaula Tantricism of Abhinavagupta in the Non-Dual Shaivism of Kashmir*. SUNY Press.
    - *Kashmiri Śaiva philosophy of consciousness, Hṛdaya as vibratory center.*

100. **Singh, J.** (1980). *Pratyabhijñāhridayam: The Secret of Self-Recognition*. Motilal Banarsidass.
    - *Kashmiri Śaiva doctrine of recognition (Pratyabhijñā) and self-reflexive awareness (svasaṃvedana).*

101. **Dyczkowski, M. S. G.** (1987). *The Doctrine of Vibration: An Analysis of the Doctrines and Practices of Kashmir Shaivism*. SUNY Press.
    - *Analysis of Spanda (vibration) and Saṃvedana as mirror-like consciousness.*

102. **Ingalls, D. H. H., Masson, J. M., & Patwardhan, M. V.** (1990). *The Dhvanyāloka of Ānandavardhana with the Locana of Abhinavagupta*. Harvard University Press.
    - *Critical edition with translation of foundational Sanskrit poetics texts.*

103. **Iyer, K. A. S.** (1977). *Bhartṛhari: A Study of the Vākyapadīya in the Light of Ancient Commentaries*. Motilal Banarsidass.
    - *Scholarly study of Bhartṛhari's philosophy of language and Sphoṭa doctrine.*

104. **Alackapally, S.** (2010). "The Sphoṭa of Language and the Experience of Śabdatattva." *Journal of Dharma*, 35(3), 204–213.
    - *Peer-reviewed analysis of Sphoṭa as linguistic and metaphysical concept.*

105. **Torella, R., et al.** (2017). "Studies on Bhartṛhari and the Pratyabhijñā: The Case of svasaṃvedana." *Religions*, 8(8), 145. MDPI. DOI: 10.3390/rel8080145.
    - *Peer-reviewed study on self-awareness in Bhartṛhari and Kashmiri Śaivism.*

106. **Kellner, B.** (2010). "Self-Awareness (Svasaṃvedana) in Dignāga's Pramāṇasamuccaya and -Vṛtti: A Close Reading." *Journal of Indian Philosophy*, 38(3), 203–231.
    - *Peer-reviewed philological analysis of Buddhist epistemology of self-awareness.*

107. **Liao, J.** (2024). "Does Memory Reflect the Function of Smṛti? Exploring the Concept of the Recollecting Mind in the Cheng Weishi Lun." *Religions*, 15(6), 632. DOI: 10.3390/rel15060632.
    - *Peer-reviewed analysis of Smṛti in Buddhist Yogācāra phenomenology.*

108. **Yao, Z.** (2005). *The Buddhist Theory of Self-Cognition*. Routledge.
    - *Academic monograph on Buddhist theories of self-awareness and consciousness.*

109. **Buswell, R. E., & Lopez, D. S.** (2014). *The Princeton Dictionary of Buddhism*. Princeton University Press.
    - *Canonical reference on Buddhist terms: vedanā, smṛti, saṃjñā, karuṇā.*

110. **Patañjali.** *Yoga Sūtra* 1.11. *Anubhūta-viṣaya-asampramoṣaḥ smṛtiḥ*.
    - *Classical definition: "Memory is the retention of images of objects that have been experienced, without distortion."*

---

## Psychology, Empathy & Auditory Neuroscience

111. **Rogers, C. R.** (1957). "The necessary and sufficient conditions of therapeutic personality change." *Journal of Consulting Psychology*, 21(2), 95–103.
    - *Foundational paper on therapeutic empathy: congruence, unconditional positive regard, empathic understanding.*

112. **Elliott, R., Bohart, A. C., Watson, J. C., & Murphy, D.** (2018). "Therapist empathy and client outcome: An updated meta-analysis." *Psychotherapy*, 55(4), 399–410.
    - *Meta-analysis of 82 samples, 6,138 clients. r = .28, d = .58. Client-perceived empathy > objective accuracy.*

113. **Norcross, J. C., & Wampold, B. E.** (2018). "A new therapy for each patient: Evidence-based relationships and responsiveness." *Journal of Clinical Psychology*, 74(11), 1889–1906.
    - *Large-scale meta-analysis (295 studies) on therapeutic alliance as robust outcome predictor.*

114. **Flückiger, C., Del Re, A. C., Wampold, B. E., & Horvath, A. O.** (2018). "The alliance in adult psychotherapy: A meta-analytic synthesis." *Psychotherapy*, 55(4), 316–340.
    - *Meta-analytic synthesis confirming alliance as cross-modality outcome predictor.*

115. **Wampold, B. E.** (2015). "How important are the common factors in psychotherapy? An update." *World Psychiatry*, 14(3), 270–277.
    - *Review: common factors (alliance, empathy, expectations) account for more outcome variance than specific techniques.*

116. **Julia, G. J., Romate, J., Allen, J. G., & Rajkumar, E.** (2024). "Compassionate communication: a scoping review." *Frontiers in Communication*, 8, 1294586.
    - *Scoping review of 5,862 records, 57 final articles. Seven dimensions of compassionate communication.*

117. **Porges, S. W.** (1995). "Orienting in a defensive world: Mammalian modifications of our evolutionary heritage. A Polyvagal Theory." *Psychophysiology*, 32(4), 301–318.
    - *Foundational paper on ventral vagal complex and social engagement system.*

118. **Porges, S. W.** (2011). *The Polyvagal Theory: Neurophysiological Foundations of Emotions, Attachment, Communication, and Self-Regulation*. W. W. Norton.
    - *Definitive monograph on Polyvagal Theory and neurobiology of safety.*

119. **Ooishi, Y., Mukai, H., Watanabe, K., Kawato, S., & Kashino, M.** (2017). "Increase in salivary oxytocin and decrease in salivary cortisol after listening to relaxing slow-tempo and exciting fast-tempo music." *PLOS ONE*, 12(12), e0189075.
    - *Empirical study: auditory stimuli increase oxytocin, decrease cortisol, correlate with HRV.*

120. **Kumar, S., Joseph, S., Gander, P. E., Barascud, N., Halpern, A. R., & Griffiths, T. D.** (2016). "A brain system for auditory working memory." *The Journal of Neuroscience*, 36(16), 4492–4505.
    - *fMRI study: auditory cortex, hippocampus, and inferior frontal gyrus form functionally connected working memory network.*

121. **Barascud, N., Pearce, M. T., Griffiths, T. D., Friston, K. J., & Chait, M.** (2016). "Brain responses in humans reveal ideal observer-like sensitivity to complex acoustic patterns." *Proceedings of the National Academy of Sciences*, 113(5), E616–E625.
    - *PNAS: auditory system operates as ideal observer, predictive not passive.*

122. **Bianco, R., Harrison, P. M. C., Hu, M., Bolger, C., Picken, S., Pearce, M. T., & Chait, M.** (2020). "Long-term implicit memory for sequential auditory patterns in humans." *eLife*, 9, e56073.
    - *Implicit auditory memories form rapidly and persist for months with resistance to interference.*

123. **Bianco, R., Hall, E. T. R., Pearce, M. T., & Chait, M.** (2023). "Implicit auditory memory in older listeners: From encoding to 6-month retention." *Current Research in Neurobiology*, 5, 100115.
    - *Aging affects encoding speed but not long-term implicit auditory memory accessibility.*

124. **Strauss, A., Wöstmann, M., & Obleser, J.** (2012). "Adverse listening conditions and memory load drive a common alpha oscillatory network." *The Journal of Neuroscience*, 32(36), 12376–12383.
    - *MEG: acoustic degradation and memory load compete for common executive control network.*

125. **Yang, J., Tang, X., Lin, S., Jiang, L., Wei, K., Cao, X., Wan, L., Wang, J., Ding, H., & Li, C.** (2023). "Altered auditory processes pattern predicts cognitive decline in older adults." *Frontiers in Aging Neuroscience*, 15, 1230939.
    - *Auditory MMN amplitude decline as early biomarker of neurodegeneration.*

---

## Learning Science & Myth Debunking

126. **Dale, E.** (1946). *Audio-Visual Methods in Teaching* (rev. 1954, 1969). Dryden Press, New York.
    - *Primary text: Cone of Experience contains NO percentages or retention claims in any edition.*

127. **Masters, K.** (2013). "Edgar Dale's Pyramid of Learning in medical education: A literature review." *Medical Teacher*, 35(11), e1584–e1593.
    - *Systematic review: 43 papers uncritically cite Pyramid; no original research found.*

128. **Masters, K.** (2020). "Edgar Dale's Pyramid of Learning in medical education: Further expansion of the myth." *Medical Education*, 54(1), 22–32.
    - *Follow-up: citations increasing; "The Pyramid is rubbish, the statistics are rubbish."*

129. **Subramony, D. P., Molenda, M., Betrus, A. K., & Thalheimer, W.** (2014). "Mythical Retention Data & The Corrupted Cone." *Educational Technology*.
    - *Peer-reviewed debunking of the Learning Pyramid myth.*

130. **Thalheimer, W.** (2006). "People remember 10%, 20%... Oh Really?" *Work-Learning Research*. https://www.worklearning.com/2006/05/01/people_remember/
    - *Industry analysis: no research data supports the retention percentages.*

---

## Cultural Appropriation, AI Ethics & Privacy

131. **ISMIR 2021.** "East Asian Philosophies and the Ethics of Music AI."
    - *Citing Hantrakul on cultural appropriation in timbre transfer; O'Neil and Gunn's Ethical Matrix.*

132. **King, J., et al.** (Stanford Institute for Human-Centered AI). (2025). "Study exposes privacy risks of AI chatbot conversations." *Stanford News*, October 15.
    - *Six leading U.S. AI companies feed user inputs into training by default; privacy documentation "often unclear."*

133. **GDPR (EU) 2016/679, Article 17.** "Right to erasure ('right to be forgotten')."
    - *Legal basis for selective amnesia architecture requirement.*

134. **MIT Sloan & BCG.** (2024). Responsible AI research. Cited in Sopra Steria.
    - *Companies prioritizing responsible AI experience nearly 30% fewer AI failures.*

135. **Jiang, Z., et al.** (2026). "Hear You in Silence: Designing for Active Listening in Human Interaction with Conversational Agents Using Context-Aware Pacing." *arXiv:2602.06134*.
    - *Five context-aware pacing strategies for conversational agents: Reflective, Facilitative, Empathic, Holding Space, Immediate.*

136. **Jack, R. E., et al.** (2014). "Facial expression signaling supports the discrimination of four categories." *Current Biology*. University of Glasgow.
    - *Challenge to Ekman's 6-basic model; suggests only 4 discriminable categories.*

137. **Hejmadi, A., et al.** (2000). Cross-cultural identification of Rasa emotions. Cited in Mukherjee (2021) "Dancing with Nine Colours." *PhilArchive*.
    - *Behavioral study demonstrating cross-cultural recognition of Rasa emotions.*

138. **Treasure, J.** (2011). "5 ways to listen better." TED Talk.
    - *RASA framework: Receive, Appreciate, Summarize, Ask.*

139. **Chowkase, A. A.** (2023). "Social and emotional learning for the greater good: Expanding the circle of human concern." *Social and Emotional Learning: Research, Practice, and Policy*, 1, 100003.
    - *Yale Center for Emotional Intelligence: operationalization of Samvedana as SEL curriculum.*

140. **Yale Center for Emotional Intelligence / Greater Good Science Center, UC Berkeley.** (2025). "What If SEL Were About Making the World a Better Place?" *Greater Good Magazine*.
    - *Samvedana curriculum: care and concern for others, encompassing humanity and nature.*

---

*Bibliography updated: 2026-04-28*  
*Previous entries: 89 (2026-04-27)*  
*New entries: 51 (90–140)*  
*Total entries: 140*  
*New coverage: Sanskrit Philosophy (20), Buddhist Phenomenology (6), Psychology/Empathy (15), Auditory Neuroscience (5), Learning Science (5), AI Ethics/Privacy (5)*
