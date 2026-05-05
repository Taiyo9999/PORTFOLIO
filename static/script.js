const form = document.getElementById("postForm");

if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
}

if (form) {
    form.addEventListener("submit", function(e) {
        e.preventDefault();

        const title = document.getElementById("title").value;
        const content = document.getElementById("content").value;
        const formData = new FormData(form);
        
        if (title === "" || content === "") {
            alert("내용을 입력하세요");
            return;
        }

        fetch("/add_post", {
            method: "POST",
            body: formData
        })
        .then(response => response.json().then(data => {
            if (!response.ok) {
                throw new Error(data.message || "게시글 작성에 실패했습니다.");
            }

            return data;
        }))
        .then(data => {
            if (window.location.pathname === "/") {
                saveBoardScroll();
                window.location.href = "/?section=board";
            } else {
                location.reload();
            }
        })
        .catch(error => {
            alert(error.message);
        });
    });
}

const btn = document.querySelector(".menu_btn");
const menu = document.querySelector(".dropdown_menu");

if (btn && menu) {
    const closeMenu = () => {
        menu.classList.remove("active");
        btn.setAttribute("aria-expanded", "false");
        menu.setAttribute("aria-hidden", "true");
    };

    const openMenu = () => {
        menu.classList.add("active");
        btn.setAttribute("aria-expanded", "true");
        menu.setAttribute("aria-hidden", "false");
    };

    btn.addEventListener("click", (e) => {
        e.stopPropagation();

        if (menu.classList.contains("active")) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    menu.addEventListener("click", (e) => {
        e.stopPropagation();
    });

    document.addEventListener("click", () => {
        closeMenu();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeMenu();
        }
    });
}

const pages = Array.from(document.querySelectorAll(".page_content")).map((pageContent) => {
    return {
        title: pageContent.dataset.title,
        subtitle: pageContent.dataset.subtitle,
        image: pageContent.dataset.image,
        label: pageContent.dataset.label,
        detailTitle: pageContent.querySelector(".page_content_title").textContent,
        detailText: pageContent.querySelector(".page_content_text").textContent
    };
});

const coverImage = document.querySelector(".cover_image");
const trackTitle = document.querySelector(".track_title");
const trackSubtitle = document.querySelector(".track_subtitle");
const progressFill = document.querySelector(".progress_fill");
const progressKnob = document.querySelector(".progress_knob");
const currentTime = document.querySelector(".current_time");
const totalTime = document.querySelector(".total_time");
const prevButton = document.querySelector(".prev_btn");
const nextButton = document.querySelector(".next_btn");
const playButton = document.querySelector(".play_btn");
const heartButton = document.querySelector(".heart_btn");
const shuffleButton = document.querySelector(".shuffle_btn");
const firstPageButton = document.querySelector(".first_page_btn");
const detailSection = document.querySelector(".page_detail");
const detailCloseButton = document.querySelector(".detail_close_btn");
const detailLabel = document.querySelector(".detail_label");
const detailTitle = document.querySelector(".detail_title");
const detailText = document.querySelector(".detail_text");
const boardPanel = document.querySelector(".board_panel");

const urlParams = new URLSearchParams(window.location.search);
const sectionParam = urlParams.get("section");
let currentPageIndex = 0;

if (sectionParam) {
    const sectionTitle = sectionParam.toUpperCase() === "MYINFO" ? "MY INFO" : sectionParam.toUpperCase();
    const sectionIndex = pages.findIndex((page) => page.title === sectionTitle);

    if (sectionIndex !== -1) {
        currentPageIndex = sectionIndex;
    }
}

if (urlParams.has("keyword")) {
    currentPageIndex = pages.findIndex((page) => page.title === "BOARD");
}
let detailTop = 0;
let detailScrollLocked = false;

if (currentPageIndex === 0) {
    window.scrollTo(0, 0);
}

const getDetailTop = () => {
    return detailSection.getBoundingClientRect().top + window.scrollY;
};

const saveBoardScroll = () => {
    sessionStorage.setItem("boardScrollY", String(window.scrollY));
};

const renderPage = () => {
    const page = pages[currentPageIndex];
    const progress = pages.length === 1 ? 0 : (currentPageIndex / (pages.length - 1)) * 100;

    if (coverImage) {
        coverImage.classList.add("changing");

        setTimeout(() => {
            coverImage.src = page.image;
            coverImage.alt = `${page.title} 이미지`;
            coverImage.classList.remove("changing");
        }, 120);
    }

    if (trackTitle) {
        trackTitle.textContent = page.title;
    }

    if (trackSubtitle) {
        trackSubtitle.textContent = page.subtitle;
    }

    if (progressFill) {
        progressFill.style.width = `${progress}%`;
    }

    if (progressKnob) {
        progressKnob.style.left = `${progress}%`;
    }

    if (currentTime) {
        currentTime.textContent = `0:0${currentPageIndex}`;
    }

    if (totalTime) {
        totalTime.textContent = `0:0${pages.length - 1}`;
    }

    if (detailLabel) {
        detailLabel.textContent = page.label;
    }

    if (detailTitle) {
        detailTitle.textContent = page.detailTitle;
    }

    if (detailText) {
        detailText.textContent = page.detailText;
    }

    if (detailSection) {
        detailSection.classList.toggle("show_board", page.title === "BOARD");
        detailSection.classList.toggle("show_myinfo", page.title === "MY INFO");
    }
};

const movePage = (direction) => {
    currentPageIndex = (currentPageIndex + direction + pages.length) % pages.length;
    renderPage();
};

const moveToPage = (title) => {
    const nextIndex = pages.findIndex((page) => page.title === title);

    if (nextIndex === -1) {
        return;
    }

    currentPageIndex = nextIndex;
    renderPage();
    openDetail();
};

const openDetail = (shouldScroll = true) => {
    detailSection.classList.add("active");
    detailScrollLocked = false;

    requestAnimationFrame(() => {
        detailTop = getDetailTop();

        if (shouldScroll) {
            detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        setTimeout(() => {
            detailScrollLocked = true;
        }, 650);
    });
};

const closeDetail = () => {
    detailScrollLocked = false;
    sessionStorage.removeItem("boardScrollY");
    detailSection.classList.remove("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
};

if (prevButton && nextButton && playButton) {
    prevButton.addEventListener("click", () => {
        movePage(-1);
    });

    nextButton.addEventListener("click", () => {
        movePage(1);
    });

    playButton.addEventListener("click", () => {
        openDetail();
    });
}

if (heartButton) {
    heartButton.addEventListener("click", () => {
        const isActive = heartButton.classList.toggle("active");
        heartButton.setAttribute("aria-pressed", String(isActive));
    });
}

if (shuffleButton) {
    shuffleButton.addEventListener("click", () => {
        let nextIndex = currentPageIndex;

        while (nextIndex === currentPageIndex && pages.length > 1) {
            nextIndex = Math.floor(Math.random() * pages.length);
        }

        currentPageIndex = nextIndex;
        renderPage();
    });
}

if (firstPageButton) {
    firstPageButton.addEventListener("click", () => {
        currentPageIndex = 0;
        renderPage();
    });
}

if (detailCloseButton && detailSection) {
    detailCloseButton.addEventListener("click", () => {
        closeDetail();
    });
}

if (boardPanel) {
    boardPanel.addEventListener("submit", () => {
        saveBoardScroll();
    }, true);
}

window.addEventListener("scroll", () => {
    if (!detailSection || !detailSection.classList.contains("active")) {
        return;
    }

    if (!detailScrollLocked) {
        return;
    }

    if (window.scrollY < detailTop) {
        window.scrollTo(0, detailTop);
    }
});

renderPage();

if (currentPageIndex > 0 && detailSection) {
    const savedBoardScroll = Number(sessionStorage.getItem("boardScrollY"));

    if (pages[currentPageIndex].title === "BOARD" && savedBoardScroll) {
        openDetail(false);

        requestAnimationFrame(() => {
            detailTop = getDetailTop();
            window.scrollTo(0, Math.max(savedBoardScroll, detailTop));
        });
    } else {
        openDetail();
    }
}
