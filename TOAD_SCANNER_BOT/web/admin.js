const loginView = document.getElementById("loginView");
const dashboardView = document.getElementById("dashboardView");

const loginForm = document.getElementById("loginForm");
const secretInput = document.getElementById("secretInput");

const loginError = document.getElementById("loginError");
const dashboardError = document.getElementById("dashboardError");

const reportsContainer = document.getElementById("reports");
const pendingCount = document.getElementById("pendingCount");
const emptyState = document.getElementById("emptyState");

const refreshButton = document.getElementById("refreshButton");
const logoutButton = document.getElementById("logoutButton");


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginError.classList.add("hidden");

    const secret = secretInput.value.trim();

    if (!secret) {
        showLoginError("Введите административный ключ.");
        return;
    }

    try {
        const response = await fetch(
            "/api/admin/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    secret: secret
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Неверный административный ключ."
            );
        }

        secretInput.value = "";

        await openDashboard();

    } catch (error) {
        showLoginError(error.message);
    }
});


refreshButton.addEventListener(
    "click",
    loadPendingReports
);


logoutButton.addEventListener(
    "click",
    async () => {
        await fetch(
            "/api/admin/logout",
            {
                method: "POST"
            }
        );

        showLogin();
    }
);


async function checkSession() {
    try {
        const response = await fetch(
            "/api/admin/session"
        );

        if (response.ok) {
            await openDashboard();
        } else {
            showLogin();
        }

    } catch {
        showLogin();
    }
}


async function openDashboard() {
    loginView.classList.add("hidden");

    dashboardView.classList.remove("hidden");

    logoutButton.classList.remove("hidden");

    await loadPendingReports();
}


function showLogin() {
    dashboardView.classList.add("hidden");

    logoutButton.classList.add("hidden");

    loginView.classList.remove("hidden");
}


async function loadPendingReports() {
    dashboardError.classList.add("hidden");

    try {
        const response = await fetch(
            "/api/admin/reports/pending"
        );

        if (response.status === 401) {
            showLogin();
            return;
        }

        if (!response.ok) {
            throw new Error(
                "Не удалось загрузить жалобы."
            );
        }

        const data = await response.json();

        pendingCount.textContent =
            data.count ?? 0;

        renderReports(
            data.reports || []
        );

    } catch (error) {
        dashboardError.textContent =
            error.message;

        dashboardError.classList.remove(
            "hidden"
        );
    }
}


function renderReports(reports) {
    reportsContainer.innerHTML = "";

    if (reports.length === 0) {
        emptyState.classList.remove(
            "hidden"
        );

        return;
    }

    // ВАЖНО:
    // если жалобы есть, сообщение "жалоб нет"
    // обязательно скрываем.
    emptyState.classList.add(
        "hidden"
    );

    reports.forEach((report) => {
        const card =
            document.createElement("div");

        card.className =
            "report-card";

        const username =
            report.username
                ? `@${report.username}`
                : "Не указан";

        const telegramId =
            report.telegram_id ?? "Не указан";

        const name =
            report.full_name || "Не указано";

        const amount =
            report.amount || "Не указана";

        const description =
            report.description || "";

        const proofs =
            report.proofs_count ?? 0;

        card.innerHTML = `
            <div class="report-top">

                <div>
                    <div class="tag">
                        PENDING REPORT
                    </div>

                    <h3>
                        Жалоба #${report.id}
                    </h3>
                </div>

                <strong>
                    ${escapeHtml(username)}
                </strong>

            </div>


            <div class="meta">

                Telegram ID:
                <strong>
                    ${escapeHtml(
                        String(telegramId)
                    )}
                </strong>

                <br>

                Имя:
                <strong>
                    ${escapeHtml(name)}
                </strong>

                <br>

                Сумма:
                <strong>
                    ${escapeHtml(amount)}
                </strong>

                <br>

                Доказательств:
                <strong>
                    ${proofs}
                </strong>

            </div>


            <div class="description">

                <div class="tag">
                    DESCRIPTION
                </div>

                <div style="margin-top:8px;">
                    ${escapeHtml(description)}
                </div>

            </div>


            <div
                style="
                    display:grid;
                    grid-template-columns:1fr 1fr;
                    gap:10px;
                    margin-top:20px;
                "
            >

                <button
                    onclick="approveReport(${report.id})"
                >
                    ✅ ОДОБРИТЬ
                </button>

                <button
                    class="reject-button"
                    onclick="openReject(${report.id})"
                    style="
                        background:#211010;
                        color:#ff7777;
                        border:1px solid #633333;
                    "
                >
                    ❌ ОТКЛОНИТЬ
                </button>

            </div>


            <div
                id="reject-${report.id}"
                class="hidden"
                style="
                    margin-top:15px;
                    padding-top:15px;
                    border-top:1px solid #28352c;
                "
            >

                <textarea
                    id="reason-${report.id}"
                    placeholder="Причина отклонения..."
                    style="
                        width:100%;
                        min-height:90px;
                        padding:14px;
                        background:#111713;
                        border:1px solid #29382d;
                        border-radius:8px;
                        color:white;
                        resize:vertical;
                    "
                ></textarea>

                <button
                    onclick="rejectReport(${report.id})"
                    style="
                        width:100%;
                        margin-top:10px;
                        background:#7d3030;
                        color:white;
                    "
                >
                    ПОДТВЕРДИТЬ ОТКЛОНЕНИЕ
                </button>

            </div>
        `;

        reportsContainer.appendChild(
            card
        );
    });
}


function openReject(reportId) {
    const block =
        document.getElementById(
            `reject-${reportId}`
        );

    block.classList.toggle(
        "hidden"
    );
}


async function approveReport(reportId) {
    const confirmed = confirm(
        `Одобрить жалобу #${reportId}?`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            `/api/admin/reports/${reportId}/approve`,
            {
                method: "POST"
            }
        );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Не удалось одобрить жалобу."
            );
        }

        alert(
            `✅ Жалоба #${reportId} одобрена`
        );

        await loadPendingReports();

    } catch (error) {
        alert(
            "Ошибка: " + error.message
        );
    }
}


async function rejectReport(reportId) {
    const input =
        document.getElementById(
            `reason-${reportId}`
        );

    const reason =
        input.value.trim();

    if (reason.length < 3) {
        alert(
            "Введите причину отклонения."
        );

        return;
    }

    const confirmed = confirm(
        `Отклонить жалобу #${reportId}?`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            `/api/admin/reports/${reportId}/reject`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    reason: reason
                })
            }
        );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Не удалось отклонить жалобу."
            );
        }

        alert(
            `❌ Жалоба #${reportId} отклонена`
        );

        await loadPendingReports();

    } catch (error) {
        alert(
            "Ошибка: " + error.message
        );
    }
}


function showLoginError(message) {
    loginError.textContent =
        message;

    loginError.classList.remove(
        "hidden"
    );
}


function escapeHtml(value) {
    const div =
        document.createElement("div");

    div.textContent =
        String(value);

    return div.innerHTML;
}


checkSession();