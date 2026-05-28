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
    let monthlySortKey = "sales_26"; // '브랜드' | 'sales_26' | 'sales_25' | 'diff' | 'pct'
    let monthlySortOrder = "desc";   // 'asc' | 'desc'

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

        // 신규 차트 3종 (Area, BCG Scatter, Category Bar)
        const areaChartDiv = document.getElementById("chart-monthly-area");
        if (data.charts && data.charts.area) {
            areaChartDiv.parentElement.style.display = "flex";
            Plotly.newPlot("chart-monthly-area", data.charts.area.data, data.charts.area.layout, {responsive: true, displayModeBar: false});
        } else {
            areaChartDiv.parentElement.style.display = "none";
        }

        const bcgChartDiv = document.getElementById("chart-monthly-bcg");
        if (data.charts && data.charts.bcg) {
            bcgChartDiv.parentElement.style.display = "flex";
            Plotly.newPlot("chart-monthly-bcg", data.charts.bcg.data, data.charts.bcg.layout, {responsive: true, displayModeBar: false});
        } else {
            bcgChartDiv.parentElement.style.display = "none";
        }

        const categoryBarChartDiv = document.getElementById("chart-monthly-category-bar");
        if (data.charts && data.charts.category_bar) {
            categoryBarChartDiv.parentElement.style.display = "flex";
            Plotly.newPlot("chart-monthly-category-bar", data.charts.category_bar.data, data.charts.category_bar.layout, {responsive: true, displayModeBar: false});
        } else {
            categoryBarChartDiv.parentElement.style.display = "none";
        }

        // Tables populating & Dynamic Header updates
        const thSales26 = document.getElementById("th-sales-26");
        const thSales25 = document.getElementById("th-sales-25");
        if (thSales26) thSales26.querySelector(".th-text").textContent = `26년 ${month}월`;
        if (thSales25) thSales25.querySelector(".th-text").textContent = `25년 ${month}월`;

        // 정렬
        let sortedBrands = [...data.tables.all_brands];
        const key = monthlySortKey;
        const order = monthlySortOrder;

        sortedBrands.sort((a, b) => {
            let valA = a[key];
            let valB = b[key];

            if (key === "브랜드") {
                valA = a["브랜드"];
                valB = b["브랜드"];
                return order === "asc" ? valA.localeCompare(valB, "ko") : valB.localeCompare(valA, "ko");
            }

            valA = parseFloat(valA) || 0;
            valB = parseFloat(valB) || 0;
            return order === "asc" ? valA - valB : valB - valA;
        });

        populateAllBrandsTable(sortedBrands);
    }

    async function loadAndRenderBrandTrend(brandName) {
        const container = document.getElementById("brand-trend-container");
        container.style.display = "block";
        
        try {
            const response = await authFetch(`${API_BASE}/api/brand/trend?brand=${encodeURIComponent(brandName)}`);
            const trendData = await response.json();
            
            const months = Array.from({length: 12}, (_, i) => `${i + 1}월`);
            
            // 데이터를 백만원 단위로 변환 (value / 1e6)
            const sales25M = trendData.sales_25.map(v => v / 1e6);
            const sales26M = trendData.sales_26.map(v => v / 1e6);
            
            // 25년 (1~12월) - 얇고 차분한 회청색 점선 (#A6B1E1)
            const trace25 = {
                x: months,
                y: sales25M,
                name: '25년 실적',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#A6B1E1', width: 2, dash: 'dot' },
                hovertemplate: "<b>25년 %{x}</b><br>매출액: %{y:,.1f}백만원<extra></extra>",
                hoverlabel: {
                    bgcolor: 'rgba(30, 30, 30, 0.9)',
                    bordercolor: '#A6B1E1',
                    font: { color: '#A6B1E1' }
                }
            };
            
            // 26년 (1~last_month) - 굵고 선명한 코랄 레드 (#FF4D4D)
            const trace26Months = months.slice(0, trendData.last_month);
            const trace26 = {
                x: trace26Months,
                y: sales26M,
                name: '26년 실적',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#FF4D4D', width: 4 },
                marker: { size: 8 },
                hovertemplate: "<b>26년 %{x}</b><br>매출액: %{y:,.1f}백만원<extra></extra>",
                hoverlabel: {
                    bgcolor: 'rgba(30, 30, 30, 0.9)',
                    bordercolor: '#FF4D4D',
                    font: { color: '#FF4D4D' }
                }
            };
            
            const layout = {
                title: {
                    text: `📈 <b>${brandName}</b> 월별 매출 비교 추이 (단위: 백만원)`,
                    font: { size: 16 }
                },
                xaxis: { title: '월' },
                yaxis: { title: '매출액 (백만원)' },
                hovermode: 'closest',
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#E5E7EB', family: 'Outfit, system-ui, sans-serif' },
                margin: { l: 65, r: 40, t: 60, b: 40 },
                xaxis: {
                    gridcolor: 'rgba(255, 255, 255, 0.08)',
                    zerolinecolor: 'rgba(255, 255, 255, 0.15)',
                    tickfont: { color: '#9CA3AF' }
                },
                yaxis: {
                    gridcolor: 'rgba(255, 255, 255, 0.08)',
                    zerolinecolor: 'rgba(255, 255, 255, 0.15)',
                    tickfont: { color: '#9CA3AF' }
                },
                legend: {
                    orientation: 'h',
                    yanchor: 'bottom',
                    y: 1.02,
                    xanchor: 'right',
                    x: 1
                }
            };
            
            Plotly.newPlot("chart-brand-trend", [trace25, trace26], layout, {responsive: true, displayModeBar: false});
        } catch (error) {
            console.error("Brand trend chart render error:", error);
        }
    }

    function populateAllBrandsTable(rows) {
        const tbody = document.querySelector("#table-all-brands tbody");
        tbody.innerHTML = "";
        
        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">데이터가 없습니다.</td></tr>`;
            document.getElementById("brand-trend-container").style.display = "none";
            return;
        }

        rows.forEach((row, index) => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            tr.dataset.brand = row.브랜드;
            
            const diffClass = row.diff >= 0 ? "text-up" : "text-down";
            const diffSign = row.diff > 0 ? "+" : "";
            const pctSign = row.pct > 0 ? "+" : "";

            tr.innerHTML = `
                <td><strong>${row.브랜드}</strong></td>
                <td class="num-col">${formatNumber(row.sales_26)}</td>
                <td class="num-col">${formatNumber(row.sales_25)}</td>
                <td class="num-col ${diffClass}">${diffSign}${formatNumber(row.diff)}</td>
                <td class="num-col ${diffClass}">${pctSign}${row.pct}%</td>
            `;

            tr.addEventListener("click", () => {
                const allRows = tbody.querySelectorAll("tr");
                allRows.forEach(r => r.style.background = "transparent");
                tr.style.background = "var(--primary-glow)";
                loadAndRenderBrandTrend(row.브랜드);
            });

            tbody.appendChild(tr);
        });

        // 기본값으로 매출액이 가장 높은 첫 번째 행 선택
        if (rows.length > 0) {
            const firstRow = tbody.querySelector("tr");
            firstRow.style.background = "var(--primary-glow)";
            loadAndRenderBrandTrend(rows[0].브랜드);
        }
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
                document.getElementById("dashboard-title").textContent = "📊 EZ-Insight 대시보드";
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

    // 테이블 헤더 클릭 이벤트 리스너 등록
    const tableHeaderThs = document.querySelectorAll("#table-all-brands thead th");
    tableHeaderThs.forEach(th => {
        th.addEventListener("click", () => {
            const key = th.dataset.key;
            if (!key) return;

            if (monthlySortKey === key) {
                monthlySortOrder = monthlySortOrder === "asc" ? "desc" : "asc";
            } else {
                monthlySortKey = key;
                monthlySortOrder = "desc";
            }

            // 헤더 아이콘 갱신
            tableHeaderThs.forEach(t => {
                const icon = t.querySelector("i");
                if (icon) {
                    const tKey = t.dataset.key;
                    if (tKey === monthlySortKey) {
                        icon.className = monthlySortOrder === "asc" ? "fa-solid fa-sort-up" : "fa-solid fa-sort-down";
                    } else {
                        icon.className = "fa-solid fa-sort";
                    }
                }
            });

            // 테이블 및 뷰 다시 그리기
            if (currentMode === "monthly") {
                renderMonthlyView();
            }
        });
    });

    // Run Initializer
    init();
});
