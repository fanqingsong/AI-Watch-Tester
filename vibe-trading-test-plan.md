# Vibe-Trading Comprehensive Test Plan

## Application Overview

Vibe-Trading is an AI-powered quantitative trading strategy research platform that enables users to describe trading strategies in natural language and have agents generate code, run backtests, and optimize strategies in real-time. The platform supports multiple markets (A-shares, US/HK equities, crypto), provides pre-built alpha factors, session management, and comprehensive configuration options.

## Test Scenarios

### 1. Navigation and Basic Access

**Seed:** `tests/seed.spec.ts`

#### 1.1. Home Page Access and Navigation

**File:** `tests/navigation/home-page.spec.ts`

**Steps:**
  1. Navigate to http://127.0.0.1:8899/
    - expect: Home page loads successfully with title 'Vibe-Trading — vibe trading with your professional financial agent team'
    - expect: Hero section displays with heading 'AI-Powered Quant Strategy Research'
    - expect: Navigation bar displays with links: Home, Agent, Alpha Zoo, Settings, Correlation Matrix
    - expect: Sidebar displays session list with existing conversations
  2. Click on 'Agent' navigation link
    - expect: Page redirects to /agent URL
    - expect: Agent page displays with example prompts and categories
    - expect: Chat interface is visible with text input box
  3. Click on 'Alpha Zoo' navigation link
    - expect: Page redirects to /alpha-zoo URL
    - expect: Alpha Zoo page displays with 452 pre-built quant alphas
    - expect: Filter options are visible: search box, Zoo dropdown, Theme dropdown, Universe dropdown
  4. Click on 'Settings' navigation link
    - expect: Page redirects to /settings URL
    - expect: Settings page displays with configuration sections
    - expect: Local API access, LLM Settings, and Data Source Settings sections are visible
  5. Click on 'Correlation Matrix' navigation link
    - expect: Page redirects to /correlation URL
    - expect: Correlation Matrix page displays with input fields
    - expect: Asset codes textbox, window selection buttons, and method selection buttons are visible

### 2. Home Page Features

**Seed:** `tests/seed.spec.ts`

#### 2.1. Home Page Hero Section

**File:** `tests/home/hero-section.spec.ts`

**Steps:**
  1. Navigate to home page and examine hero section
    - expect: Heading 'AI-Powered Quant Strategy Research' is displayed
    - expect: Descriptive paragraph explains the platform's capabilities
    - expect: 'Start Research' button is visible and clickable
  2. Click 'Start Research' button
    - expect: Redirects to /agent page
    - expect: Agent chat interface is displayed

#### 2.2. Home Page Feature Cards

**File:** `tests/home/feature-cards.spec.ts`

**Steps:**
  1. Examine the four feature cards displayed on home page
    - expect: 'AI Agent' card with description 'Natural language strategy generation with ReAct reasoning'
    - expect: 'Built-in Backtest' card with description '7 data sources across A-shares, US/HK & Crypto'
    - expect: 'Real-time Streaming' card with description 'Watch the agent think, call tools, and iterate'
    - expect: 'Strategy Replay' card with description 'Trade journal analyzer + Shadow Account'

#### 2.3. Logo and Brand Navigation

**File:** `tests/home/logo-navigation.spec.ts`

**Steps:**
  1. Click on 'Vibe-Trading' logo in sidebar
    - expect: Redirects to home page (/)
    - expect: Home page content is displayed

### 3. Agent Page and Chat Interface

**Seed:** `tests/seed.spec.ts`

#### 3.1. Agent Page Initial Display

**File:** `tests/agent/initial-display.spec.ts`

**Steps:**
  1. Navigate to /agent page without session
    - expect: Page displays welcome message 'Describe a trading strategy to get started'
    - expect: Feature list displays: Finance Skills Library, Swarm Agent Teams, Auto-Discovered Tools, etc.
    - expect: Example prompts are organized by categories: Multi-Market Backtest, Research & Analysis, Swarm Teams, Document & Web Research, Trade Journal, Trading Connectors, Shadow Account
    - expect: Text input box is visible with placeholder 'e.g. Create a dual MA crossover strategy for 000001.SZ, backtest 2024'

#### 3.2. Example Prompt Buttons

**File:** `tests/agent/example-prompts.spec.ts`

**Steps:**
  1. Scroll through example prompt categories
    - expect: Six categories are visible: Multi-Market Backtest, Research & Analysis, Swarm Teams, Document & Web Research, Trade Journal, Trading Connectors, Shadow Account
    - expect: Each category has 2-4 example prompts
  2. Click on 'Cross-Market Portfolio' example button
    - expect: Button displays description: 'A-shares + crypto + US equities with risk-parity optimizer'
    - expect: Clicking populates the chat input or initiates the request

#### 3.3. Session List Display

**File:** `tests/agent/session-list.spec.ts`

**Steps:**
  1. Examine the session list in sidebar
    - expect: Recent sessions are displayed with titles
    - expect: Each session has 'Rename' and 'Delete?' buttons
    - expect: Sessions are clickable to load
    - expect: 'New Chat' link is visible at top of session list
  2. Click on an existing session title
    - expect: Page navigates to the selected session
    - expect: Session content is displayed

### 4. Alpha Zoo Page

**Seed:** `tests/seed.spec.ts`

#### 4.1. Alpha Zoo Initial Display

**File:** `tests/alpha-zoo/initial-display.spec.ts`

**Steps:**
  1. Navigate to /alpha-zoo page
    - expect: Page displays heading '452 pre-built quant alphas across 4 zoos'
    - expect: Subheading explains the zoo sources: Qlib, Kakushadze 101, GTJA 191, Academic Anomalies
    - expect: Four zoo cards are displayed with feature counts
    - expect: Search and filter controls are visible
    - expect: Alpha catalogue table displays list of alphas with columns

#### 4.2. Alpha Zoo Filtering

**File:** `tests/alpha-zoo/filtering.spec.ts`

**Steps:**
  1. Use the search box to filter alphas
    - expect: Search box accepts text input
    - expect: Alpha list filters based on search query (ID or nickname)
    - expect: Results update in real-time
  2. Select 'Zoo' dropdown and choose different zoo
    - expect: Dropdown shows options: All zoos, Qlib 158, Kakushadze 101, GTJA 191, Academic Anomalies
    - expect: Selecting a zoo filters the alpha list
    - expect: Only alphas from selected zoo are displayed
  3. Select 'Theme' dropdown and choose different theme
    - expect: Dropdown shows theme options: All themes, liquidity, microstructure, momentum, quality, reversal, sentiment, value, volatility, volume
    - expect: Selecting a theme filters the alpha list
    - expect: Only alphas with selected theme are displayed

### 5. Settings Page

**Seed:** `tests/seed.spec.ts`

#### 5.1. Settings Page Initial Display

**File:** `tests/settings/initial-display.spec.ts`

**Steps:**
  1. Navigate to /settings page
    - expect: Page displays heading 'Settings'
    - expect: Subheading explains configuration purpose
    - expect: Three main sections are visible: Local API access, LLM Settings, Data Source Settings

#### 5.2. LLM Connection Settings

**File:** `tests/settings/llm-connection.spec.ts`

**Steps:**
  1. Examine LLM Settings - Connection section
    - expect: 'Provider' dropdown shows multiple options: OpenRouter (default), OpenAI, DeepSeek, Gemini, etc.
    - expect: 'Model' textbox shows default value 'deepseek/deepseek-v4-pro'
    - expect: 'Base URL' textbox shows default value 'https://openrouter.ai/api/v1'
    - expect: 'API key' textbox has placeholder 'Leave blank to keep the current key'
    - expect: 'Use provider defaults' button is visible
  2. Change Provider dropdown selection
    - expect: Model and Base URL fields update to recommended values for selected provider

#### 5.3. Data Source Settings

**File:** `tests/settings/data-source.spec.ts`

**Steps:**
  1. Examine Data Source Settings section
    - expect: 'Tushare token' label is visible
    - expect: Helper text explains Tushare usage for China A-share data
    - expect: 'Clear saved Tushare token' checkbox is visible
  2. Enter Tushare token value and click 'Save data source settings'
    - expect: Token is saved to agent/.env file
    - expect: Success message or confirmation is displayed

### 6. Correlation Matrix Page

**Seed:** `tests/seed.spec.ts`

#### 6.1. Correlation Matrix Initial Display

**File:** `tests/correlation/initial-display.spec.ts`

**Steps:**
  1. Navigate to /correlation page
    - expect: Page displays heading 'Correlation Matrix'
    - expect: Asset codes textbox is visible with default value 'BTC-USDT,ETH-USDT,SPY,AAPL'
    - expect: Window (days) section shows buttons: 30d, 60d, 90d, 180d, 365d
    - expect: Method section shows buttons: pearson, spearman
    - expect: Compute button is visible

#### 6.2. Correlation Matrix Computation

**File:** `tests/correlation/computation.spec.ts`

**Steps:**
  1. Enter asset codes, select window and method, click Compute
    - expect: Computation is initiated
    - expect: Correlation matrix is generated and displayed
    - expect: Results show correlation coefficients between asset pairs

### 7. Session Management

**Seed:** `tests/seed.spec.ts`

#### 7.1. Session List Display

**File:** `tests/sessions/list-display.spec.ts`

**Steps:**
  1. Examine session list in sidebar
    - expect: Recent sessions are displayed with titles
    - expect: Each session has 'Rename' and 'Delete?' buttons
    - expect: Sessions are clickable to load
    - expect: 'New Chat' link is visible at top of session list

#### 7.2. Session Rename Functionality

**File:** `tests/sessions/rename.spec.ts`

**Steps:**
  1. Click 'Rename' button on a session
    - expect: Rename interface appears
    - expect: Input field shows current session name
  2. Enter new session name and confirm
    - expect: Session title is updated in the list
    - expect: Success message appears

#### 7.3. Session Delete Functionality

**File:** `tests/sessions/delete.spec.ts`

**Steps:**
  1. Click 'Delete?' button on a session
    - expect: Confirmation dialog appears
    - expect: Warning message explains deletion consequences
  2. Confirm session deletion
    - expect: Session is removed from the list
    - expect: Success message appears

### 8. Sidebar and UI Controls

**Seed:** `tests/seed.spec.ts`

#### 8.1. Sidebar Display and Layout

**File:** `tests/ui/sidebar-layout.spec.ts`

**Steps:**
  1. Examine sidebar on any page
    - expect: Sidebar is visible on left side of page
    - expect: Logo, navigation links, and session list are visible
    - expect: Version number 'v0.1.9' is visible at bottom

#### 8.2. Dark Mode Toggle

**File:** `tests/ui/dark-mode.spec.ts`

**Steps:**
  1. Click 'Dark' button in sidebar
    - expect: Theme toggles between dark and light modes
    - expect: Visual appearance changes immediately

#### 8.3. Sidebar Collapse/Expand

**File:** `tests/ui/sidebar-collapse.spec.ts`

**Steps:**
  1. Click 'Collapse' button in sidebar
    - expect: Sidebar collapses or expands
    - expect: Main content area adjusts its width
