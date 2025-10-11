(function() {
  "use strict";

  let isSequenceMode = false;
  let firstKey = "";
  let sequenceTimeout;

  let isScrolling = false;
  let scrollDirection = 0;
  let scrollSpeed = 0;
  let lastScrollTime = 0;
  let keysPressed = new Set();

  const SCROLL_DISTANCE = 30; // Base scroll distance per frame
  const MAX_SCROLL_SPEED = 5; // Maximum speed multiplier
  const SCROLL_ACCELERATION = 0.05; // How fast we accelerate

  const MIN_FRAME_TIME = 16; // ~60fps

  function isTyping() {
    const activeElement = document.activeElement;
    return (
      activeElement &&
      (activeElement.tagName === "INPUT" ||
        activeElement.tagName === "TEXTAREA" ||
        activeElement.contentEditable === "true" ||
        activeElement.isContentEditable)
    );
  }

  function getScrollContainer() {
    const mainFrame = document.querySelector(".main-frame");
    const body = document.body;
    const documentElement = document.documentElement;

    if (mainFrame && mainFrame.scrollHeight > mainFrame.clientHeight) {
      return mainFrame;
    }

    if (body.scrollHeight > body.clientHeight) {
      return body;
    }

    return documentElement;
  }

  function scrollLoop() {
    const now = performance.now();

    if (now - lastScrollTime < MIN_FRAME_TIME) {
      if (isScrolling) {
        requestAnimationFrame(scrollLoop);
      }
      return;
    }

    lastScrollTime = now;

    if (!isScrolling || scrollDirection === 0) {
      return;
    }

    const container = getScrollContainer();
    const isWindowScroll =
      container === document.body || container === document.documentElement;
    const scrollAmount = SCROLL_DISTANCE * scrollSpeed * scrollDirection;

    if (isWindowScroll) {
      window.scrollBy(0, scrollAmount);
    } else {
      container.scrollTop += scrollAmount;
    }

    if (isScrolling) {
      requestAnimationFrame(scrollLoop);
    }
  }

  function startScroll(direction) {
    if (isScrolling && scrollDirection === direction) {
      scrollSpeed = Math.min(
        scrollSpeed + SCROLL_ACCELERATION,
        MAX_SCROLL_SPEED,
      );
    } else {
      scrollDirection = direction;
      scrollSpeed = 1;
      isScrolling = true;
      requestAnimationFrame(scrollLoop);
    }
  }

  function stopScroll() {
    isScrolling = false;
    scrollDirection = 0;
    scrollSpeed = 0;
  }

  function findPaginationLinks() {
    const paginationContainer = document.querySelector(".pagination-links");
    if (!paginationContainer) return { prev: null, next: null };

    const prevLink = paginationContainer.querySelector('a[rel="prev"]');
    const nextLink = paginationContainer.querySelector('a[rel="next"]');

    return { prev: prevLink, next: nextLink };
  }


  function navigatePage(direction) {
    const { prev, next } = findPaginationLinks();

    if (direction === "prev" && prev) {
      prev.click();
    } else if (direction === "next" && next) {
      next.click();
    }
  }

  function handleSequence(key) {
    if (!isSequenceMode) {
      // next/previous page
      if (key === "]" || key === "[") {
        isSequenceMode = true;
        firstKey = key;

        sequenceTimeout = setTimeout(() => {
          isSequenceMode = false;
          firstKey = "";
        }, 1000);

        return true;
      }
    } else {
      clearTimeout(sequenceTimeout);
      isSequenceMode = false;

      if (firstKey === "]" && key === "]") {
        navigatePage("next");
        firstKey = "";
        return true;
      } else if (firstKey === "[" && key === "[") {
        navigatePage("prev");
        firstKey = "";
        return true;
      }
      firstKey = "";
    }
    return false;
  }

  function handleKeydown(event) {
    if (isTyping()) return;
    // extra keys
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) {
      return;
    }
    const key = event.key;
    let handled = false;

    keysPressed.add(key);

    if (handleSequence(key)) {
      handled = true;
    } else if (!isSequenceMode) {
      switch (key) {
        case "j":
          startScroll(1);
          handled = true;
          break;
        case "k":
          startScroll(-1);
          handled = true;
          break;
      }
    }
    if (handled) {
      event.preventDefault();
      event.stopPropagation();
    }
  }
  function handleKeyup(event) {
    const key = event.key;
    keysPressed.delete(key);
    if (
      (key === "j" || key === "k") &&
      !keysPressed.has("j") &&
      !keysPressed.has("k")
    ) {
      stopScroll();
    }
  }
  function init() {
    // start listeners
    document.addEventListener("keydown", handleKeydown);
    document.addEventListener("keyup", handleKeyup);
    window.addEventListener("blur", stopScroll);
  }

  // load on ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
