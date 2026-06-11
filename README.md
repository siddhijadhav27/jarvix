# Jarvix

**Jarvix** is an AI-powered crypto command center — a unified platform for managing, analyzing, and interacting with blockchain assets through natural language and intelligent automation

## Overview

Jarvix combines modern AI capabilities with deep crypto infrastructure to deliver:

- **Conversational AI Interface** — Interact with your portfolio, execute trades, and query on-chain data using natural language.
- **Multi-Chain Support** — Seamlessly connect across Ethereum, BSC, Polygon, and other EVM-compatible networks.
- **Real-Time Analytics** — Live price feeds, portfolio tracking, and market intelligence.
- **Secure Wallet Integration** — Non-custodial architecture with support for popular wallets.
- **Automated Workflows** — Set up alerts, recurring trades, and AI-driven strategies.

## Tech Stack

- **Frontend:** Next.js 14, Tailwind CSS, shadcn/ui
- **Backend / API:** Python FastAPI
- **AI / LLM:** Kimi API (OpenAI-compatible)
- **Blockchain:** Web3.js / Ethers.js
- **Database:** PostgreSQL + Redis + TimescaleDB
- **Deployment:** Docker, Vercel

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/siddhijadhav27/jarvix.git
cd jarvix

# Install dependencies
npm install

# Start the development server
npm run dev
```

## Project Structure

```
jarvix/
├── apps/
│   ├── web/                 # Next.js 14 frontend
│   │   ├── app/             # App Router
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities
│   └── api/                 # FastAPI backend
│       ├── routers/         # API routes
│       ├── models/          # Database models
│       └── services/        # Business logic
├── packages/
│   └── ai/                  # Shared AI logic
│       ├── intent.py        # NLP classifier
│       ├── memory.py        # Context manager
│       └── predict.py       # Price prediction
├── docker/
│   ├── docker-compose.yml   # All services
│   ├── Dockerfile.web       # Frontend
│   └── Dockerfile.api       # Backend
├── docs/
│   ├── api.md               # API documentation
│   └── setup.md             # Installation guide
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions
├── .gitignore
├── LICENSE
└── README.md
```

## Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jarvix
REDIS_URL=redis://localhost:6379

# API Keys
KIMI_API_KEY=your_kimi_api_key
OPENAI_API_KEY=your_openai_api_key

# Blockchain
INFURA_KEY=your_infura_key
ETHERSCAN_API_KEY=your_etherscan_key

# Security
JWT_SECRET=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key

# External Services
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET=your_binance_secret
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/refresh` | Refresh token |

### Portfolio
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio` | Get portfolio summary |
| GET | `/api/portfolio/assets` | List all assets |
| POST | `/api/portfolio/rebalance` | Rebalance portfolio |

### Trading
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/trade/execute` | Execute trade |
| GET | `/api/trade/history` | Trade history |
| GET | `/api/trade/orders` | Active orders |

### AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/chat` | Chat with Jarvix |
| POST | `/api/ai/predict` | Price prediction |
| GET | `/api/ai/insights` | Market insights |

## Roadmap

### Phase 0: Foundation (Current)
- [x] GitHub repository setup
- [x] Monorepo structure
- [x] CI/CD pipeline
- [ ] Docker setup
- [ ] Database schema

### Phase 1: Core Intelligence
- [ ] Kimi API integration
- [ ] Natural language commands
- [ ] Context awareness
- [ ] Basic predictions

### Phase 2: Trading
- [ ] Paper trading
- [ ] DCA strategy
- [ ] Stop-loss
- [ ] Live trading

### Phase 3: Voice
- [ ] Whisper STT
- [ ] Fish Speech TTS
- [ ] Wake word
- [ ] Voice commands

### Phase 4: Security
- [ ] Slither integration
- [ ] Scam detection
- [ ] OSINT
- [ ] Incident response

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please read our [Contributing Guide](docs/setup.md) for details.

## Support

For support, email support@jarvix.ai or join our [Discord community](https://discord.gg/jarvix).

## Acknowledgments

- Built with [Kimi API](https://kimi.com) for AI capabilities
- Powered by [FastAPI](https://fastapi.tiangolo.com) and [Next.js](https://nextjs.org)
- Blockchain integration via [Web3.js](https://web3js.readthedocs.io)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

Built with ❤️ by Siddhi Rajan Jadhav
# Deploy fix
# Deploy trigger Thu Jun 11 09:30:09 PM IST 2026
# Deploy trigger Thu Jun 11 09:30:23 PM IST 2026
# Deploy fix v2 Thu Jun 11 09:40:05 PM IST 2026
# Deploy fix v3 Thu Jun 11 09:45:58 PM IST 2026
# Force redeploy Thu Jun 11 10:05:09 PM IST 2026
# Force redeploy v2 Thu Jun 11 10:13:14 PM IST 2026
# Force redeploy v3 Thu Jun 11 10:19:33 PM IST 2026
# Force redeploy v4 Thu Jun 11 10:24:42 PM IST 2026
# Force redeploy v6 Thu Jun 11 11:25:08 PM IST 2026
# Force redeploy v7 Thu Jun 11 11:30:14 PM IST 2026
# Force redeploy v8 Thu Jun 11 11:39:54 PM IST 2026
# Force redeploy v9 Thu Jun 11 11:42:25 PM IST 2026
# Force redeploy v10 Thu Jun 11 11:45:47 PM IST 2026
# Force redeploy v11 Fri Jun 12 12:09:42 AM IST 2026
# Force redeploy v12 Fri Jun 12 12:31:32 AM IST 2026
