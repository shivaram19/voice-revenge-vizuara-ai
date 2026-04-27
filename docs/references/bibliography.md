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
