(() => {
    // Stop any previous auto-next watcher
    clearInterval(window.autoNext);

    let clicked = false;

    window.autoNext = setInterval(() => {
        try {
            // Reacquire the live SCORM document every pass
            const outer = document.querySelector("iframe");

            const viewer = outer?.contentDocument
                ?.querySelector("#scorm_viewer_iframe");

            const d = viewer?.contentDocument;

            if (!d) {
                return;
            }

            // First range input is the slide progress control
            const p = d.querySelectorAll('input[type="range"]')[0];

            // Next button
            const next = d.querySelector("#next");

            if (!p || !next) {
                return;
            }

            // Read timeline position
            const current = Number(
                p.getAttribute("aria-valuenow")
            );

            const max = Number(
                p.getAttribute("aria-valuemax")
            );

            // --------------------------------------------------
            // FINISHED
            //
            // Some slides stop slightly short of aria-valuemax.
            // Treat anything within 100 units of max as complete.
            // --------------------------------------------------
            if (current >= max - 100 && !clicked) {

                clicked = true;

                console.log(
                    `FINISHED: ${current} / ${max} -> NEXT`
                );

                next.click();

                return;
            }

            // --------------------------------------------------
            // STILL PLAYING
            //
            // This also re-arms the watcher after moving to
            // the next slide.
            // --------------------------------------------------
            if (current < max - 100) {

                clicked = false;

                console.log(
                    `Watching: ${current} / ${max}`
                );
            }

        } catch (e) {

            console.log(
                "AUTO-NEXT error:",
                e
            );
        }

    }, 1000);

    console.log("AUTO-NEXT v4 STARTED");
})();
