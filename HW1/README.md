Comparing different kinds of plagiarism detectors.
We will have 5 github repos containing C# code.
We have 6 code snippets from each repo, which we then transform into positive cases (slight edits that should count as plagiarism) and negative cases (complete rewrites that do the same job but should **NOT** count as plagiarism).

We have 4 different methods for evaluating plagiarism:
1. Direct embedding search
2. Asking gpt-4o in OpenAI API what it thinks
3. RAG
4. Hybrid RAG

We then compare tradeoffs, accuracy, threshold changes etc as appropriate to figure out when to use which method and with what parameters

## Repos
1. Mixed Reality Toolkit for Unity
    - Accelerate mixed reality development in Unity
    - https://github.com/MixedRealityToolkit/MixedRealityToolkit-Unity
2. Unity ROS TCP Connector
    - Allows Robot Operating System (ROS) to connect to Unity
    - https://github.com/Unity-Technologies/ROS-TCP-Connector
3. .NET Bio
    - Bioinformatics library for .NET
    - https://github.com/dotnetbio/bio
4. BotSharp
    - AI Multi-Agent Framework in .NET
    - https://github.com/SciSharp/BotSharp
5. BrainFlow C# Package
    - Obtain, parse and analyze EEG, EMG, ECG, and other kinds of data from biosensors.
    - https://github.com/brainflow-dev/brainflow/tree/d74ed6631cd587f5bf473bf26623507ad7adbab9/csharp_package

## 📂 Data Layout
```
snippets/
│
├── MixedRealityToolkit/
│   ├── snippet_1/
│   │   ├── original.cs
│   │   ├── plagiarised/
│   │   │   ├── plag_1.cs
│   │   │   ├── plag_2.cs
│   │   │   ├── plag_3.cs
│   │   └── non-plagiarised/
│   │       ├── non_1.cs
│   │       ├── non_2.cs
│   │   │   ├── non_3.cs
│   ├── snippet_2/
│   └── ...
│
├── ROS_TCP_Connector/
│   └── snippet_1/ ... snippet_6/
│
├── DotNetBio/
│   └── snippet_1/ ... snippet_6/
│
├── BotSharp/
│   └── snippet_1/ ... snippet_6/
│
└── BrainFlow/
    └── snippet_1/ ... snippet_6/
```

## Data Collection & Transformation
From each repo I picked 6 snippets (sometimes a method sometimes an entire .cs file) that seemed most different from each other while each implementing a different non-trivial logic.

I then (with some mix of manual work and ChatGPT assistance) derived 3 plagiarised and 3 non-plagiarised alternatively implemented version of each snippet.

Plagiarised versions are slight reshuffles and renames while keeping core logic same,
while non-plagiarised versions extract first principles and rebuild the logic from scratch and go a different route (verified both by myself manually and double-checked by GPT-5.1 Thinking)