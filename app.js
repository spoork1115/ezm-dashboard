/**
 * EasyMembers BI Dashboard Frontend Logic
 * Integrated with FastAPI Backend & Plotly.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // API Config (Uses localhost:8000 for local development, and relative path for Vercel)
    const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : window.location.origin;

    // App State
    let currentMode = "trend"; // "trend" | "portfolio" | "monthly"
    let currentMonth = null;
    let maxMonth = 12;
    let dataCache = {
        trend: null,
        portfolio: null,
        monthly: {}
    };

    // Elements
    const loginOverlay = document.getElementById("login-overlay");
    const loginPasswordInput = document.getElementById("login-password");
    const loginBtn = document.getElementById("login-btn");
    const loginErrorMsg = document.getElementById("login-error-msg");
    const loader = document.getElementById("global-loader");
    const dashboardSubtitle = document.getElementById("dashboard-subtitle");
    const baseMonthText = document.getElementById("base-month-text");
    const monthSelect = document.getElementById("month-select");
    const monthlyControls = document.getElementById("monthly-controls-container");
    const viewTrend = document.getElementById("viewport-trend");
    const viewPortfolio = document.getElementById("viewport-portfolio");
    const viewMonthly = document.getElementById("viewport-monthly");

    // Initialize App
    async function init() {
        const token = localStorage.getItem("easy_bi_token");
        if (!token) {
            showLoginOverlay();
            return;
        }

        showLoader();
        try {
            const response = await authFetch(`${API_BASE}/api/meta`);
            const meta = await response.json();
            currentMonth = meta.last_month;
            maxMonth = meta.last_month;

            // Populate Month Select
            monthSelect.innerHTML = "";
            for (let m = 1; m <= maxMonth; m++) {
                const opt = document.createElement("option");
                opt.value = m;
                opt.textContent = `${m}월`;
                if (m === currentMonth) opt.selected = true;
                monthSelect.appendChild(opt);
            }

            // Update Headings
            baseMonthText.textContent = `기준월: 2026년 ${currentMonth}월 누적 데이터(YTD) 반영`;
            dashboardSubtitle.classList.remove("loading-shimmer-text");
            dashboardSubtitle.textContent = `실시간 구글 스프레드시트 연동 BI 애널리틱스`;

            hideLoginOverlay();

            // Initial view load
            await loadModeData();
        } catch (error) {
            console.error(error);
            if (error.message !== "Unauthorized") {
                dashboardSubtitle.textContent = "API 서버 연결 오류. 잠시 후 다시 시도해 주세요.";
                dashboardSubtitle.style.color = "#EF4444";
            }
        } finally {
            hideLoader();
        }
    }

    // Auth & Overlay Helpers
    function showLoginOverlay() {
        loginOverlay.classList.remove("hidden");
        loginPasswordInput.focus();
    }

    function hideLoginOverlay() {
        loginOverlay.classList.add("hidden");
    }

    async function authFetch(url, options = {}) {
        const token = localStorage.getItem("easy_bi_token");
        if (!options.headers) {
            options.headers = {};
        }
        if (token) {
            options.headers["Authorization"] = `Bearer ${token}`;
        }
        options.headers["Content-Type"] = "application/json";
        
        const response = await fetch(url, options);
        if (response.status === 401) {
            localStorage.removeItem("easy_bi_token");
            dataCache = { trend: null, portfolio: null, monthly: {} };
            showLoginOverlay();
            throw new Error("Unauthorized");
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response;
    }

    // Loader controls
    function showLoader() { loader.classList.add("active"); }
    function hideLoader() { loader.classList.remove("active"); }

    // Value Formatting Helpers
    function formatWon(value) {
        if (value === null || value === undefined) return "-";
        const billion = value / 1e8;
        return billion.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "억 원";
    }

    function formatNumber(value) {
        if (value === null || value === undefined) return "-";
        return Math.round(value).toLocaleString();
    }

    function updateBadge(elId, val, showPlus = true, suffix = "%") {
        const el = document.getElementById(elId);
        if (!el) return;
        const parent = el.parentElement;
        
        el.className = "trend-badge " + (val >= 0 ? "up" : "down");
        const plusSign = showPlus && val > 0 ? "+" : "";
        el.innerHTML = (val >= 0 ? '<i class="fa-solid fa-caret-up"></i>' : '<i class="fa-solid fa-caret-down"></i>') + ` ${plusSign}${val.toFixed(1)}${suffix}`;
    }

    // Main Data Loading Orchestrator
    async function loadModeData() {
        showLoader();
        try {
            if (currentMode === "trend") {
                await renderTrendView();
            } else if (currentMode === "portfolio") {
                await renderPortfolioView();
            } else if (currentMode === "monthly") {
                await renderMonthlyView();
            }
        } catch (error) {
            console.error("View rendering error:", error);
        } finally {
            hideLoader();
        }
    }

    // Render 1: Trend Mode
    async function renderTrendView() {
        if (!dataCache.trend) {
            const response = await authFetch(`${API_BASE}/api/trend`);
            dataCache.trend = await response.json();
        }

        const data = dataCache.trend;
        
        // KPIs
        document.getElementById("tot-24").textContent = formatWon(data.kpi.tot_24);
        document.getElementById("tot-25").textContent = formatWon(data.kpi.tot_25);
        document.getElementById("tot-26-ytd").textContent = formatWon(data.kpi.tot_26_ytd);
        document.getElementById("tot-26-fcst").textContent = formatWon(data.kpi.tot_26_fcst);

        document.getElementById("kpi-ytd-title").textContent = `26년 누적 실적(${maxMonth}개월)`;

        // Badges
        updateBadge("yoy-25", data.kpi.yoy_25, true, "% (YoY)");
        updateBadge("yoy-26-ytd", data.kpi.yoy_26_ytd, true, "%");
        updateBadge("yoy-26-fcst", data.kpi.yoy_26_fcst, true, "%");

        // Charts
        Plotly.newPlot("chart-waterfall", data.charts.waterfall.data, data.charts.waterfall.layout, {responsive: true, displayModeBar: false});
        Plotly.newPlot("chart-line", data.charts.line.data, data.charts.line.layout, {responsive: true, displayModeBar: false});
    }

    // Render 2: Portfolio Mode
    async function renderPortfolioView() {
        if (!dataCache.portfolio) {
            const response = await authFetch(`${API_BASE}/api/portfolio`);
            dataCache.portfolio = await response.json();
        }

        const data = dataCache.portfolio;

        // Charts
        Plotly.newPlot("chart-scatter", data.charts.scatter.data, data.charts.scatter.layout, {responsive: true, displayModeBar: false});
        Plotly.newPlot("chart-heatmap", data.charts.heatmap.data, data.charts.heatmap.layout, {responsive: true, displayModeBar: false});
    }

    // Render 3: Monthly Mode
    async function renderMonthlyView() {
        const month = parseInt(monthSelect.value);
        if (!dataCache.monthly[month]) {
            const response = await authFetch(`${API_BASE}/api/monthly?month=${month}`);
            dataCache.monthly[month] = await response.json();
        }

        const data = dataCache.monthly[month];

        // Headers
        document.getElementById("m-kpi-25-title").textContent = `25년 ${month}월 매출`;
        document.getElementById("m-kpi-26-title").textContent = `26년 ${month}월 매출`;

        // KPIs
        document.getElementById("m-sales-25").textContent = formatWon(data.kpi.sales_25);
        document.getElementById("m-sales-26").textContent = formatWon(data.kpi.sales_26);
        document.getElementById("m-top-brand").textContent = data.kpi.top_brand;

        // Badges
        updateBadge("m-yoy", data.kpi.yoy, true, "% (YoY)");

        // Pareto Chart
        const chartParetoDiv = document.getElementById("chart-pareto");
        if (data.chart) {
            chartParetoDiv.style.display = "block";
            Plotly.newPlot("chart-pareto", data.chart.data, data.chart.layout, {responsive: true, displayModeBar: false});
        } else {
            chartParetoDiv.style.display = "none";
        }

        // Tables populating
        populateTable("table-up", data.tables.top_up, "up");
        populateTable("table-down", data.tables.top_down, "down");
    }

    function populateTable(tableId, rows, direction) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        tbody.innerHTML = "";
        
        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">데이터가 없습니다.</td></tr>`;
            return;
        }

        rows.forEach(row => {
            const tr = document.createElement("tr");
            const diffClass = direction === "up" ? "text-up" : "text-down";
            const diffSign = row.diff > 0 ? "+" : "";
            const pctSign = row.pct > 0 ? "+" : "";

            tr.innerHTML = `
                <td><strong>${row.브랜드}</strong></td>
                <td class="num-col">${formatNumber(row.sales_26)}</td>
                <td class="num-col">${formatNumber(row.sales_25)}</td>
                <td class="num-col ${diffClass}">${diffSign}${formatNumber(row.diff)}</td>
                <td class="num-col ${diffClass}">${pctSign}${row.pct}%</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // --- Event Listeners ---

    // Sidebar Mode Toggles
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", async (e) => {
            const btn = e.currentTarget;
            if (btn.classList.contains("active")) return;

            navItems.forEach(i => i.classList.remove("active"));
            btn.classList.add("active");

            currentMode = btn.dataset.mode;

            // Viewport visibility toggling
            viewTrend.style.display = currentMode === "trend" ? "block" : "none";
            viewPortfolio.style.display = currentMode === "portfolio" ? "block" : "none";
            viewMonthly.style.display = currentMode === "monthly" ? "block" : "none";

            // Sidebar control visibility
            monthlyControls.style.display = currentMode === "monthly" ? "block" : "none";

            // Handle title and fetch data
            if (currentMode === "trend") {
                document.getElementById("dashboard-title").textContent = "📊 이지멤버스 BI 대시보드";
            } else if (currentMode === "portfolio") {
                document.getElementById("dashboard-title").textContent = "🧩 브랜드 포트폴리오 분석";
            } else if (currentMode === "monthly") {
                document.getElementById("dashboard-title").textContent = "📅 세부 월별 실적 분석";
            }

            await loadModeData();
        });
    });

    // Month Dropdown Select Change
    monthSelect.addEventListener("change", async () => {
        if (currentMode === "monthly") {
            await renderMonthlyView();
        }
    });

    // Portfolio Sub Tabs Toggle
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            const targetTab = e.currentTarget.dataset.tab;
            
            tabButtons.forEach(b => b.classList.remove("active"));
            e.currentTarget.classList.add("active");

            document.getElementById("tab-scatter").style.display = targetTab === "scatter" ? "block" : "none";
            document.getElementById("tab-heatmap").style.display = targetTab === "heatmap" ? "block" : "none";

            // Reflow Plotly charts to adapt to size
            if (targetTab === "scatter" && dataCache.portfolio) {
                Plotly.Plots.resize(document.getElementById("chart-scatter"));
            } else if (targetTab === "heatmap" && dataCache.portfolio) {
                Plotly.Plots.resize(document.getElementById("chart-heatmap"));
            }
        });
    });

    // Login Submit Handler
    async function handleLogin() {
        const password = loginPasswordInput.value.trim();
        if (!password) return;

        loginErrorMsg.style.display = "none";
        try {
            const response = await fetch(`${API_BASE}/api/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ password })
            });

            if (!response.ok) {
                throw new Error("Invalid password");
            }

            const data = await response.json();
            localStorage.setItem("easy_bi_token", data.token);
            loginPasswordInput.value = "";
            
            await init();
        } catch (err) {
            loginErrorMsg.style.display = "flex";
            const card = document.querySelector(".login-card");
            card.style.animation = "none";
            setTimeout(() => {
                card.style.animation = "shake 0.35s ease-in-out";
            }, 10);
        }
    }

    loginBtn.addEventListener("click", handleLogin);
    loginPasswordInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleLogin();
    });

    // Run Initializer
    init();
});
