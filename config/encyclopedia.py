"""
AML / Crypto Compliance Encyclopedia
Comprehensive Reference for Crypto Exchange AML Professionals
Version 1.0 | February 2026

This knowledge base powers Case Walker's expertise in AML/crypto compliance topics.
"""

AML_ENCYCLOPEDIA = """AML / CRYPTO COMPLIANCE ENCYCLOPEDIA
Comprehensive Reference for Crypto Exchange AML Professionals
Version 1.0 | February 2026 | 19 Source Materials | 120+ Glossary Terms | 15+ Case Studies

1. COMPLIANCE FRAMEWORKS & STANDARDS

1.1 VASP Decision-Making Framework (DP-1 through DP-5)

The VASP compliance decision-making process follows five sequential Decision Points (DPs):

DP-1: Customer Identification (KYC/KYB/CDD) - Identity verification, document collection, risk profiling, PEP/sanctions screening
DP-2: Transaction Analysis (Transaction monitoring) - Source of funds check, pattern analysis, threshold monitoring, blockchain analytics
DP-3: Risk Assessment (Risk scoring) - Assign risk level (low/medium/high), determine EDD requirements, counterparty risk evaluation
DP-4: Decision & Action (Compliance decision) - Approve/reject/escalate, SAR filing decision, account restrictions if needed
DP-5: Ongoing (Continuous oversight) - Periodic reviews, transaction monitoring, sanctions list updates, risk re-assessment

1.2 FATF Standards

The Financial Action Task Force (FATF) sets global AML/CFT standards. Key recommendations for crypto:

- Recommendation 15 (New Technologies): VASPs must be licensed/registered, implement AML/CFT programs, be subject to supervision
- Recommendation 16 (Travel Rule): VASPs must collect and share originator/beneficiary info for transactions above threshold ($1,000/EUR 1,000)
- FATF Updated Guidance (2021): Expanded definitions, DeFi coverage, stablecoin guidance, NFT risk assessment
- Asset Recovery: Countries must enable tracing, freezing, and confiscation of virtual assets used in crime

1.3 Regulatory Landscape by Jurisdiction

- United States: BSA, FinCEN guidance, state MTLs. MSB registration, SAR/CTR filing, OFAC sanctions compliance
- European Union: MiCA (2024), AMLD6, TFR. CASP licensing, Travel Rule compliance, comprehensive AML/CFT programs
- United Kingdom: FCA registration, MLR 2017. FCA crypto registration, risk-based AML approach
- Singapore: Payment Services Act (PSA). MAS licensing for DPT services
- UAE: VARA (Dubai), ADGM, SCA. Jurisdiction-specific licensing, risk-based AML

2. PROFESSIONAL CERTIFICATIONS

- CAMS (ACAMS) - Gold standard AML certification. $1,695+ | 3-6 months prep
- CCAS (ACAMS) - Crypto-specific AML. $995+ | 2-3 months
- CFCS (ACFCS) - Financial crime specialist. $1,250+ | 3-6 months
- CKYC (ACAMS) - KYC specialist. $695+ | 1-2 months
- TRM Certified Investigator (TRM Labs) - Blockchain forensics
- Chainalysis Reactor Certification - Investigation using Reactor platform
- CGSS (ACAMS) - Global sanctions specialist. $995+ | 2-3 months
- CFE (ACFE) - Certified Fraud Examiner. $450+ | 3-6 months

3. BLOCKCHAIN ANALYTICS PLATFORMS

3.1 Enterprise Platforms

- Chainalysis (Reactor, KYT, Storyline): 1B+ clustered addresses, 55K+ services, 250+ cryptos. Enterprise ($100K+/yr)
- Elliptic (Navigator, Investigator, GLASS): 100B+ data points, 40+ blockchains. GLASS ML model auto-detects patterns. Enterprise ($80K+/yr)
- TRM Labs (Forensics, Transaction Monitoring): 200M+ assets, 80+ blockchains, $10B+ seizures supported. Enterprise (custom)
- CertiK (SkyInsights): Security audit + AML convergence. Address labeling, risk scoring
- Scorechain: 200+ blockchains. DeFi transaction analysis, smart contract monitoring

3.2 Mid-Market & Specialized Platforms

- Arkham Intelligence: AI Ultra engine, entity-based (not just address), Intel Exchange bounties
- Nansen: 500M+ labeled wallets, Smart Money tracking, token god mode
- AMLBot / Btrace: Quick address risk check, API integration. $99-$2,499/mo
- Sumsub: KYC/KYB/AML, document verification, 220+ jurisdictions. From $499/mo
- Sardine: Device intelligence, behavioral biometrics, real-time ML fraud detection
- SlowMist (MistTrack, MistEye): On-chain AML/KYT, threat early-warning, exploit forensics

4. ANONYMIZATION TECHNIQUES

4.1 Mixers & Tumblers

- Centralized Mixers: Custodial. User sends funds, mixer returns different funds. Examples: Helix, Bitcoin Fog, Blender.io, Sinbad.io. Most seized/sanctioned
- Decentralized (CoinJoin): Non-custodial. Multiple users combine inputs. Examples: Wasabi Wallet, Samourai Whirlpool, JoinMarket. Operational (legal challenges)
- Smart Contract Mixers: Pool + zk-proofs. Example: Tornado Cash. OFAC sanctioned (Aug 2022)
- Privacy Coins: Built-in protocol-level anonymity. Monero (ring signatures), Zcash (zk-SNARKs), Dash (CoinJoin)

Key Stats: $82B crypto ML in 2025 (Chainalysis). Tornado Cash: 254K ETH ($605M) deposited H1 2025. YoMix: 5x growth in 2023.

4.2 Chain Hopping (Cross-Chain Laundering)

Chain hopping = rapidly converting stolen funds between blockchains via bridges, DEX, and swap services.
$743.8M sent from illicit addresses to bridges in 2023 (up 2.4x from 2022). 68% of 2024 laundering used chain-hopping.

Tools used:
- Cross-Chain Bridges: THORChain, Avalanche Bridge, Chainflip, Incognito
- DeFi Aggregators: 1inch, Curve Finance, Uniswap. $1.2B laundered through aggregators
- Instant Swap (No-KYC): eXch, FixedFloat. eXch used in Bybit laundering
- Complementary Mixers: Tornado Cash + bridges, YoMix, Wasabi

4.3 Peel Chains

Peel chains = transferring crypto through a series of wallets, with small amounts peeled off at each step.
The crypto equivalent of smurfing/structuring in traditional finance.

How it works: Initial large sum (e.g., 100 BTC) -> small fraction peeled to exchange -> remainder to new address -> repeat 100-1000+ times.
Detection: Characteristic "comet tail" visual pattern. Decreasing balance series. ML models can detect.

5. DEANONYMIZATION & FORENSIC TECHNIQUES

5.1 Address Clustering

Foundation of all blockchain analytics. Groups addresses belonging to same entity.
Chainalysis: 1B+ addresses clustered. Nansen: 500M+ wallets labeled.

Bitcoin (UTXO) Heuristics:
- Common-Input Ownership (Co-Spend): Multiple inputs in same TX = one owner. Most fundamental
- Change Address Detection: UTXO remainder returns to sender. Links transaction chains
- Peeling Chain Detection: Large sum sequentially peeled = malicious indicator
- Address Reuse Analysis: Reused addresses = obvious clustering
- Behavioral Patterns: Timing, amounts, frequency, gas/fee settings

Ethereum (Account Model) Heuristics:
- Deposit Address Heuristic: Exchange unique deposit per client -> consolidate to hot wallet. Most effective (Victor 2020)
- Multiple Airdrop Participation: Same addresses in multiple airdrops = airdrop farmer
- Token Authorization (Self Auth): ERC-20 allowance/approval patterns reveal connections
- Event-Based (Chainalysis): Factory contract events for DeFi protocol association

5.2 Dusting Attacks

Sending tiny amounts of crypto to addresses to break privacy by linking through subsequent transactions.
Scale: ~71,000 wallets affected (Samourai). BTC dust threshold: ~546 satoshi.
Used by: Analytics firms, law enforcement, tax authorities, malicious actors.

6. SMART CONTRACT ANALYSIS

6.1 OWASP Smart Contract Top 10 (2025)

SC01: Access Control - $953.2M losses. #1 killer. Ronin, Bybit = key compromise
SC02: Price Oracle Manipulation - $8.8M. Manipulated price feeds
SC03: Logic Errors - $63.8M. Business logic flaws
SC04: Lack of Input Validation - $14.6M. Nomad Bridge = verification bug
SC05: Reentrancy Attacks - $35.7M. The DAO hack ($70M, 2016) = classic
SC06: Unchecked External Calls - $550.7K
SC07: Flash Loan Attacks - $33.8M. New entry 2025
SC08: Integer Overflow/Underflow - Solidity 0.8+ has built-in protection
SC09: Insecure Randomness
SC10: Denial of Service

6.2 DeFi Scam Typology

- Honeypot: Contract blocks token selling after purchase. 300K+ scam tokens
- Hidden Mint: Developer creates unlimited tokens. 2M+ investors defrauded
- Rug Pull: Developer removes liquidity. $7.7B stolen (2021)
- Fake Ownership Renunciation: renounceOwnership() is fake
- Hidden Fee Modifier: Sell fee set to 100% after investors buy
- SelfDestruct / DelegateCall: Contract destroyed or logic manipulated. 1 in 4 NFT contracts show high-risk patterns

6.3 Smart Contract Audit Firms

- CertiK: 5,500+ audits, 83K+ vulnerabilities. SkyInsights AML API
- Trail of Bits: Created Slither, Echidna, Manticore. Research-level
- OpenZeppelin: Industry-standard Solidity libraries. Ethernaut security game
- Hacken: ISO 27001. HackenProof BugBounty (10K+ ethical hackers)
- SlowMist: Asia leader. MistTrack (AML), MistEye (threat monitoring)
- Halborn: Enterprise red teaming

7. NESTED EXCHANGES

A nested exchange provides crypto trading through an account on another regulated exchange, often without KYC.

7.1 OFAC-Sanctioned Crypto Exchanges

- Suex OTC (Sep 2021): FIRST sanctioned crypto exchange. Czech-registered, Russia operated. 40%+ illicit transactions
- Chatex (Nov 2021): P2P exchange. 50%+ illicit. Direct ties to Suex. Ransomware facilitation
- Garantex (Apr 2022 / Aug 2025): $96B volume, $1.3B illicit. Conti, Hydra, Lazarus connections. Rebranded to Grinex
- Grinex (Aug 2025): Garantex successor. A7A5 ruble-backed token for user compensation
- Bitpapa / NetEx24 / AWEX (Sep 2024): Russian exchanges. Telegram bot-based, no AML/KYC
- Cryptex (Sep 2024): Financial services for cybercriminals
- Tornado Cash (Aug 2022): Smart contract mixer. Used by Lazarus Group
- Sinbad.io / Blender.io (Nov 2023 / May 2022): Bitcoin mixers linked to Lazarus Group

7.2 Garantex Case Study: Hydra Effect

Demonstrates the "hydra effect": sanctioning one exchange leads to successors.
Garantex (2019-2025) -> Grinex (Mar 2025+) -> MKAN Coin (Telegram-based) -> Exved (fiat-to-USDT).
Each successor inherits infrastructure, personnel, and laundering blueprints.
OFAC now sanctions successors, executives, supporting companies, and even tokens (A7A5).

8. MAJOR CASE STUDIES

8.1 Bridge Exploits Comparison

- Ronin (Mar 2022): $625M. 5/9 validator keys compromised (social engineering). Lazarus Group
- Wormhole (Feb 2022): $325M. Missing signature verification. Jump Crypto covered losses
- Nomad (Aug 2022): $190M. Verification bug. Mob attack (hundreds of wallets). Gurevich extradited May 2025
- BNB Bridge (Oct 2022): $586M. Proof verification bug
- Harmony Horizon (Jun 2022): $100M. 2/5 multisig keys. Lazarus Group

2022 Total Bridge Losses: ~$2B+. Bridges became #1 attack target.

8.2 Ronin Bridge (Axie Infinity) - $625M

Attacker: Lazarus Group (DPRK). Confirmed by FBI, OFAC.
Mechanism: Social engineering (fake LinkedIn job offer) -> malware -> 4 Sky Mavis + 1 Axie DAO key = 5/9 threshold.
173,600 ETH + 25.5M USDC. UNDETECTED FOR 6 DAYS.
Laundering: Tornado Cash -> post-OFAC: chain hopping (ETH -> BNB Chain -> USDD -> BitTorrent). ~$30M seized (5% recovery).
Lessons: 1) Social engineering > code exploits 2) Low validator threshold = catastrophic 3) 6-day detection gap 4) Triggered TC sanctions

8.3 Nomad Bridge - $190M "Mob Attack"

NOT a single attacker. Verification bug allowed ANYONE to replicate exploit = "mob attack".
Vulnerability: Misconfiguration in Replica contract process() function. OWASP SC04.
Gurevich laundering: chain hopping -> Tornado Cash -> Monero/Dash -> OTC -> offshore shell companies -> NFT washing.
Enforcement: Alexander Gurevich arrested Jerusalem (May 2025). Extradited to US.

8.4 Lazarus Group - Complete Attack Timeline

- Mar 2022: Ronin Bridge $625M (5/9 validator keys via social engineering)
- Jun 2022: Harmony Horizon $100M (2/5 multisig keys)
- Jun 2023: Atomic Wallet $100M (Sinbad mixing, chain hopping)
- Jul 2023: CoinsPaid/Alphapo $37M/$60M (social engineering, mixers)
- Sep 2023: Stake.com/CoinEx $41M/$55M (multi-chain, bridge exploitation)
- May 2024: DMM Bitcoin $305M (peel chains, coin mixers)
- Jul 2024: WazirX $235M (cross-chain bridges, DEX)
- Feb 2025: Bybit $1.5B - LARGEST EVER (DEX + THORChain + Chainflip + eXch, 68% laundered in 7 days)

Lazarus Adaptability: TC sanctioned -> DeFi chain hopping -> Sinbad -> YoMix -> THORChain + eXch.
Most sophisticated laundering operation globally.

9. RED FLAGS TAXONOMY

9.1 Transaction-Based Red Flags

- Mixer/Tumbler exposure: Funds from/to known mixers (Tornado Cash, YoMix, Wasabi)
- Peel chain patterns: Series of micro-deposits with decreasing sums
- Structuring (smurfing): Multiple transactions just below AML reporting thresholds
- Rapid sequential transfers: Fast transfers through multiple addresses
- Chain hopping indicators: Bridge usage immediately before/after deposit
- Privacy coin conversion: Conversion to/from Monero, Zcash, Dash near transaction
- Flash loan activity: Large uncollateralized transactions within single block
- Immediate cash-out: Small sums immediately converted to fiat
- Dust transaction received: Tiny amounts sent (potential dusting attack)

9.2 Address/Entity Red Flags

- Sanctioned address exposure: Transactions with OFAC SDN-listed addresses
- Darknet market exposure: Fund flows from/to known darknet marketplace
- Scam/fraud token interaction: Interaction with known honeypot, rug pull, scam token
- New/unused addresses: Funds from recently created one-time-use addresses
- High number of hops: 10+ intermediate addresses before arrival
- Nested exchange patterns: One account with anomalously high volume
- Ransomware address exposure: Fund flows from/to known ransomware addresses
- Exploit contract interaction: History includes known exploit contracts

10. OBFUSCATION METHODS: COMPARATIVE ANALYSIS

- Peel Chain: Fragmentation through address series. Medium complexity, medium detectability, high combinability
- Mixer/Tumbler: Pooling funds. High complexity, medium-low detectability, high combinability
- Chain Hop: Transfer between blockchains. High complexity, medium detectability, high combinability
- Privacy Coins: Cryptographic anonymity. Very high complexity, low detectability (Monero nearly untraceable)
- DEX Swap: Exchange without KYC. Low complexity, high detectability (on-chain data available)
- CoinJoin: Combining inputs. High complexity, medium detectability
- Nested Exchange: Trading via host exchange. Low complexity, medium detectability
- NFT Laundering: Wash trading. Medium complexity, medium-high detectability
- DeFi Lending: Deposit illicit, borrow "clean". Medium complexity, medium detectability

Multi-Layer Standard: Sophisticated actors NEVER use single technique. Standard: peel chain -> mixer -> chain hop -> DEX -> no-KYC exchange -> CEX.

11. INVESTIGATION METHODOLOGY

11.1 ZachXBT - Independent On-Chain Investigator

Methodology: On-chain analysis (Arkham, Nansen, Etherscan) + OSINT (social media, domain lookups, leaked databases) + community tips.
Notable: Jeff Huang ($70M+), BAYC phishing ring, multiple rug pull exposures.
Impact: Led to FBI investigations, exchange freezes, OFAC attention.

11.2 Fund Tracing Pipeline

1. Identification: Identify initial illicit address (LE, victim report, public intelligence)
2. Clustering: Expand to full cluster (co-spend, change address, deposit heuristics)
3. Fund Flow Tracing: Follow through hops, mixers, bridges, DEX. Visualize complete path
4. Exit Point Mapping: Identify fiat exit points (CEX deposits, P2P, OTC, nested exchanges)
5. Attribution: Link clusters to real-world entities via KYC, OSINT, LE intelligence
6. Asset Recovery: Freeze, seize, forfeit. Coordinate across jurisdictions

12. KEY STATISTICS & 2025-2026 TRENDS

12.1 Key Statistics

- Crypto ML volume: $82B in 2025 (Chainalysis/Reuters)
- Illicit entity on-chain balances: $15B (Jul 2025), 359% growth since 2020
- Direct illicit-to-exchange transfers: 15% (Q2 2025), down from 40% (2021-22)
- Cross-chain laundering (2025): $21.8B via cross-chain methods
- Smart contract exploit losses (2025): $3.35B across 630 incidents (CertiK)
- DeFi losses (2025): $649M (126 incidents, 63% of total)
- Exchange losses (2025): $1.809B (12 incidents, inc. Bybit $1.46B)
- Rug pull victims: 300K+ scam tokens, 2M+ defrauded investors
- AI-enhanced tracing improvement: 55% reduction in tracing time (TRM Labs)
- Deepfake fraud attempts (US): 1,100% increase in 2025
- Multi-chain investigations: 33% involve 3+ chains, 20% span 10+ chains

12.2 Major Trends

- Fewer incidents, larger impact: 2025 fewer security incidents but +46% total losses. Average hit $5.32M
- DeFi/stablecoin priority: FATF mid-2025 stablecoins and DeFi = priority risk areas. MiCA enforcement begins
- Cross-chain analytics arms race: Single-chain monitoring obsolete. AI tracks 5-10 chains simultaneously
- AI in compliance: Agentic AI for KYC/AML workflows. Explainability required by regulators
- AI-enabled crime: Deepfakes (+1,100%), synthetic IDs (+300%), AI-powered scam compounds
- Successor exchange pattern: Sanctioned exchanges rebrand (Garantex -> Grinex -> MKAN -> Exved)
- Security-AML convergence: CertiK SkyInsights: security audit + AML in one platform
- Audit as closed-loop: SlowMist model: pre + during + post incident
- Privacy bridge evolution: Chain Hopping 4.0: privacy bridges + zk-proofs
- Global enforcement coordination: DOJ + Interpol + regional LE = extraditions for DeFi exploits

13. GLOSSARY (SELECTED KEY TERMS)

- Address Clustering: Grouping blockchain addresses belonging to same entity. Foundation of all blockchain analytics
- AML (Anti-Money Laundering): Laws and procedures to prevent criminals from disguising illegally obtained funds
- CDD (Customer Due Diligence): Verifying customer identity and assessing risk before business relationship
- Chain Hopping: ML technique: rapid fund conversion between blockchains via bridges/DEX
- CoinJoin: Privacy technique: multiple users combine inputs in single transaction
- Common-Input Ownership: Heuristic: inputs in same transaction belong to one owner
- Cross-Chain Bridge: Software enabling asset movement between blockchains via lock-mint
- Deposit Address Heuristic: Most effective Ethereum clustering: linking exchange deposit addresses
- Dusting Attack: Sending tiny crypto amounts to deanonymize through co-spend analysis
- EDD (Enhanced Due Diligence): Additional verification for high-risk customers beyond CDD
- Entity Resolution: Linking address cluster to real person/organization
- Exit Point: Where funds leave crypto for fiat (exchange, P2P, OTC, nested exchange)
- FATF: Financial Action Task Force - intergovernmental body setting global AML/CFT standards
- Fiat Off-Ramp: Service for crypto-to-fiat conversion. Final stage of ML chain
- Flash Loan Attack: Uncollateralized loan in single transaction exploiting DeFi protocol
- Formal Verification: Mathematical proof of smart contract correctness ($200K+)
- Honeypot (Crypto): Fraudulent smart contract blocking token selling after purchase
- KYC (Know Your Customer): Identity verification process for financial services
- KYT (Know Your Transaction): Real-time transaction monitoring for suspicious activity
- Mixer/Tumbler: Service pooling crypto and redistributing to break on-chain links
- Mob Attack: Exploit where public vulnerability is copy-pasted by hundreds (Nomad, 2022)
- Nested Exchange: Crypto service trading via account on another regulated exchange, often no KYC
- OFAC SDN List: Specially Designated Nationals List of sanctioned persons/entities
- Peel Chain: ML technique: large sum through address series, small fraction peeled each step
- Privacy Coins: Cryptos with built-in anonymity: Monero (ring signatures), Zcash (zk-SNARKs)
- Reentrancy Attack: External call before state update allows repeated fund drain
- Rug Pull: Developer creates token, attracts investment, drains funds/liquidity
- SAR (Suspicious Activity Report): Report filed when suspicious transaction detected
- Smurfing/Structuring: Breaking large sum into small transactions below reporting thresholds
- Travel Rule: FATF R.16: VASPs share originator/beneficiary info for transfers above threshold
- VASP: Virtual Asset Service Provider (exchanges, wallets, etc.)
- Validator Key Compromise: Theft of validator private keys for unauthorized control
- zk-SNARKs/zk-proofs: Cryptographic method proving knowledge without revealing the information
"""

# Condensed knowledge brief for system prompt injection
# This gives Case Walker core expertise without using too many tokens
KNOWLEDGE_BRIEF = """ЭКСПЕРТНАЯ БАЗА ЗНАНИЙ КЕЙСА УОКЕРА:

VASP Compliance Framework (DP-1 - DP-5):
DP-1 Идентификация клиента (KYC/KYB/CDD), DP-2 Анализ транзакций, DP-3 Оценка рисков, DP-4 Решение (одобрить/отклонить/эскалировать/SAR), DP-5 Непрерывный мониторинг.

FATF стандарты: Рекомендация 15 (лицензирование VASP), Рекомендация 16 (Travel Rule - передача данных отправителя/получателя при транзакциях >$1000), Руководство 2021 (DeFi, стейблкоины, NFT).

Юрисдикции: США (BSA/FinCEN/OFAC), ЕС (MiCA 2024/AMLD6/TFR), UK (FCA/MLR 2017), Сингапур (PSA/MAS), ОАЭ (VARA/ADGM).

Блокчейн-аналитика: Chainalysis (1B+ кластеризованных адресов, Reactor/KYT/Storyline), Elliptic (GLASS ML-модель, 40+ блокчейнов), TRM Labs ($10B+ конфискаций), CertiK (SkyInsights - аудит+AML), Arkham (AI Ultra, разведка по сущностям), Nansen (500M+ размеченных кошельков).

Методы отмывания крипто:
- Миксеры: централизованные (Bitcoin Fog, Sinbad - санкционированы), CoinJoin (Wasabi, Samourai), смарт-контракт (Tornado Cash - OFAC санкции авг 2022)
- Chain hopping: быстрая конвертация между блокчейнами через мосты (THORChain, Chainflip), DEX, no-KYC обменники (eXch, FixedFloat). 68% отмывания 2024
- Peel chains: серия кошельков с отщеплением малых сумм на каждом шаге ("хвост кометы")
- Privacy coins: Monero (ring signatures), Zcash (zk-SNARKs)
- Многослойная схема: peel chain -> миксер -> chain hop -> DEX -> no-KYC биржа -> CEX

Деанонимизация:
- Кластеризация адресов: Common-Input Ownership, Change Address Detection, Deposit Address Heuristic (самый эффективный для Ethereum)
- Dusting attacks: микроплатежи для деанонимизации через co-spend анализ
- Методология ZachXBT: on-chain анализ + OSINT + community tips

Красные флаги: миксер-экспозиция, peel chain паттерны, structuring/smurfing, chain hopping индикаторы, privacy coin конвертация, flash loans, мгновенный кэш-аут, sanctioned address exposure, darknet exposure, exploit contract interaction.

OFAC-санкционированные биржи: Suex (первая, сен 2021), Chatex, Garantex ($96B оборота, ребренд в Grinex - "эффект гидры"), Bitpapa/NetEx24/AWEX, Cryptex, Tornado Cash.

Ключевые кейсы:
- Ronin Bridge $625M (Lazarus Group, соц. инженерия через LinkedIn, 6 дней незамечен)
- Nomad $190M ("mob attack" - сотни кошельков скопировали эксплойт, Gurevich экстрадирован)
- Bybit $1.5B (фев 2025, крупнейший в истории, Lazarus, 68% отмыто за 7 дней)

Lazarus Group (КНДР): Ronin $625M -> Harmony $100M -> Atomic $100M -> CoinsPaid $37M -> DMM $305M -> WazirX $235M -> Bybit $1.5B. Адаптируются: TC -> DeFi chain hop -> Sinbad -> YoMix -> THORChain.

Smart Contract Top 10 (OWASP 2025): #1 Access Control ($953M), #2 Price Oracle, #3 Logic Errors, #4 Input Validation (Nomad), #5 Reentrancy (The DAO), #7 Flash Loans.

DeFi скамы: Honeypot (300K+ токенов), Hidden Mint (2M+ жертв), Rug Pull ($7.7B в 2021).

Статистика 2025: $82B крипто-отмывание, $15B illicit on-chain balances, $3.35B потери от эксплойтов, deepfake fraud +1100%, 33% расследований затрагивают 3+ блокчейна.

Тренды: меньше инцидентов но +46% потерь, DeFi/стейблкоины приоритет FATF, AI в комплаенсе, AI-enabled crime, конвергенция безопасности и AML, privacy bridges + zk-proofs."""
