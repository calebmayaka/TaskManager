(function () {
    "use strict";

    const form = document.querySelector("form[data-auth-form]");
    if (!form) {
        return;
    }

    const mode = form.dataset.authForm;
    const authCard = document.getElementById("auth-card");
    const authErrors = document.querySelector("[data-auth-errors]");
    const fieldNames = mode === "register"
        ? ["email", "full_name", "password1", "password2"]
        : ["username", "password"];

    function getFieldElements(fieldName) {
        const wrapper = form.querySelector(`[data-field="${fieldName}"]`);
        const input = form.querySelector(`[name="${fieldName}"]`);
        const feedback = form.querySelector(`[data-field-feedback="${fieldName}"]`);
        return { wrapper, input, feedback };
    }

    function clearFieldState(wrapper) {
        if (!wrapper) {
            return;
        }
        wrapper.classList.remove("is-valid", "is-invalid", "is-pending");
    }

    function setFieldState(fieldName, state, message) {
        const { wrapper, feedback } = getFieldElements(fieldName);
        if (!wrapper) {
            return;
        }
        clearFieldState(wrapper);
        if (state) {
            wrapper.classList.add(state);
        }
        if (feedback) {
            feedback.textContent = message || "";
        }
    }

    function validateEmail(value) {
        if (!value) {
            return "Email is required.";
        }
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(value)) {
            return "Enter a valid email address.";
        }
        return "";
    }

    function validateField(fieldName) {
        const { input } = getFieldElements(fieldName);
        if (!input) {
            return { valid: true, message: "" };
        }
        const value = input.value.trim();

        if (mode === "login") {
            if (fieldName === "username") {
                const error = validateEmail(value);
                return { valid: !error, message: error };
            }
            if (fieldName === "password") {
                if (!value) {
                    return { valid: false, message: "Password is required." };
                }
            }
            return { valid: true, message: "" };
        }

        if (fieldName === "email") {
            const error = validateEmail(value);
            return { valid: !error, message: error };
        }
        if (fieldName === "full_name") {
            if (!value) {
                return { valid: false, message: "Full name is required." };
            }
            return { valid: true, message: "" };
        }
        if (fieldName === "password1") {
            if (!value) {
                return { valid: false, message: "Password is required." };
            }
            if (value.length < 8) {
                return { valid: false, message: "Use at least 8 characters." };
            }
            if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
                return { valid: false, message: "Use letters and numbers." };
            }
            return { valid: true, message: "Strong enough." };
        }
        if (fieldName === "password2") {
            const password1 = form.querySelector('[name="password1"]');
            const passwordValue = password1 ? password1.value : "";
            if (!value) {
                return { valid: false, message: "Please confirm your password." };
            }
            if (value !== passwordValue) {
                return { valid: false, message: "Passwords do not match." };
            }
            return { valid: true, message: "Passwords match." };
        }

        return { valid: true, message: "" };
    }

    function validateAndPaint(fieldName) {
        const result = validateField(fieldName);
        setFieldState(fieldName, result.valid ? "is-valid" : "is-invalid", result.message);
        return result.valid;
    }

    function applyServerFieldErrors() {
        fieldNames.forEach((fieldName) => {
            const { wrapper, feedback } = getFieldElements(fieldName);
            if (!wrapper || !feedback) {
                return;
            }
            const message = feedback.textContent.trim();
            if (message) {
                clearFieldState(wrapper);
                wrapper.classList.add("is-invalid");
            }
        });
    }

    function handleServerNonFieldErrors() {
        if (!authErrors) {
            return;
        }
        const combinedText = authErrors.textContent.trim().toLowerCase();
        if (!combinedText) {
            return;
        }

        if (combinedText.includes("pending approval")) {
            authErrors.classList.add("is-pending");
            if (mode === "login") {
                setFieldState("username", "is-pending", "Approval is still pending.");
                setFieldState("password", "is-pending", "Try again after admin approval.");
            }
            return;
        }

        if (mode === "login") {
            setFieldState("username", "is-invalid", "Check your email.");
            setFieldState("password", "is-invalid", "Check your password.");
            if (authCard) {
                authCard.classList.remove("shake-once");
                void authCard.offsetWidth;
                authCard.classList.add("shake-once");
            }
        }
    }

    fieldNames.forEach((fieldName) => {
        const { input, wrapper } = getFieldElements(fieldName);
        if (!input || !wrapper) {
            return;
        }

        input.addEventListener("blur", () => {
            validateAndPaint(fieldName);
            if (fieldName === "password1" && mode === "register") {
                const confirmField = form.querySelector('[name="password2"]');
                if (confirmField && confirmField.value) {
                    validateAndPaint("password2");
                }
            }
        });

        input.addEventListener("input", () => {
            if (wrapper.classList.contains("is-invalid")) {
                validateAndPaint(fieldName);
            }
            if (fieldName === "password1" && mode === "register") {
                const confirmField = form.querySelector('[name="password2"]');
                if (confirmField && confirmField.value) {
                    validateAndPaint("password2");
                }
            }
        });
    });

    form.addEventListener("submit", (event) => {
        let allValid = true;
        let firstInvalidInput = null;

        fieldNames.forEach((fieldName) => {
            const isValid = validateAndPaint(fieldName);
            if (!isValid) {
                allValid = false;
                if (!firstInvalidInput) {
                    const field = getFieldElements(fieldName);
                    firstInvalidInput = field.input;
                }
            }
        });

        if (!allValid) {
            event.preventDefault();
            if (firstInvalidInput) {
                firstInvalidInput.focus();
            }
        }
    });

    applyServerFieldErrors();
    handleServerNonFieldErrors();
})();
