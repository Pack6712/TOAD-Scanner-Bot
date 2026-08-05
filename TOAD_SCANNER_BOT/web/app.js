const form = document.getElementById("searchForm");
const input = document.getElementById("searchInput");

const result = document.getElementById("result");
const errorBox = document.getElementById("error");
const loading = document.getElementById("loading");

const resultUsername =
    document.getElementById("resultUsername");

const resultName =
    document.getElementById("resultName");

const riskScore =
    document.getElementById("riskScore");

const riskProgress =
    document.getElementById("riskProgress");

const entityId =
    document.getElementById("entityId");

const reportsCount =
    document.getElementById("reportsCount");

const entityStatus =
    document.getElementById("entityStatus");

const openEntity =
    document.getElementById("openEntity");


let currentEntityId = null;


form.addEventListener("submit", async (event) => {

    event.preventDefault();

    let username = input.value.trim();

    if (!username) {
        showError("Введите Telegram username.");
        return;
    }

    username = username.replace("@", "");

    result.classList.add("hidden");
    errorBox.classList.add("hidden");
    loading.classList.remove("hidden");

    try {

        const response = await fetch(
            `/api/search/${encodeURIComponent(username)}`
        );

        if (response.status === 404) {
            throw new Error(
                "В базе TOAD Scanner этот аккаунт не найден."
            );
        }

        if (!response.ok) {
            throw new Error(
                "Ошибка сервера. Попробуйте позже."
            );
        }

        const data = await response.json();

        currentEntityId = data.entity_id;

        resultUsername.textContent =
            data.username || "Не указан";

        resultName.textContent =
            data.display_name || "";

        riskScore.textContent =
            data.risk_score;

        riskProgress.style.width =
            `${Math.min(data.risk_score, 100)}%`;

        entityId.textContent =
            `#${data.entity_id}`;

        reportsCount.textContent =
            data.reports_count;

        entityStatus.textContent =
            (data.status || "unknown").toUpperCase();

        result.classList.remove("hidden");

    } catch (error) {

        showError(error.message);

    } finally {

        loading.classList.add("hidden");
    }
});


openEntity.addEventListener("click", () => {

    if (!currentEntityId) {
        return;
    }

    window.location.href =
        `/web/entity.html?id=${currentEntityId}`;
});


function showError(message) {

    errorBox.textContent = message;

    errorBox.classList.remove("hidden");

    result.classList.add("hidden");
}