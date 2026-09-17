let selectedRole = "CITIZEN";


function selectRole(role) {

    selectedRole = role;

    const citizenButton =
        document.getElementById("citizenRole");

    const authorityButton =
        document.getElementById("authorityRole");


    citizenButton.classList.remove("active");
    authorityButton.classList.remove("active");


    if (role === "CITIZEN") {

        citizenButton.classList.add("active");

    } else {

        authorityButton.classList.add("active");

    }
}


document
    .getElementById("loginForm")
    .addEventListener("submit", async function (event) {

        event.preventDefault();


        const email =
            document.getElementById("email").value;

        const password =
            document.getElementById("password").value;

        const errorMessage =
            document.getElementById("errorMessage");


        errorMessage.textContent = "";


        try {

            /*
             * Login
             */

            const response = await fetch(
                "http://127.0.0.1:8000/api/auth/login",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail || "Login failed"
                );

            }


            /*
             * Save JWT
             */

            localStorage.setItem(
                "access_token",
                data.access_token
            );


            /*
             * Get logged-in user
             */

            const userResponse = await fetch(
                "http://127.0.0.1:8000/api/auth/me",
                {
                    method: "GET",

                    headers: {
                        "Authorization":
                            `Bearer ${data.access_token}`
                    }
                }
            );


            const user = await userResponse.json();


            if (!userResponse.ok) {

                throw new Error(
                    "Could not retrieve user information"
                );

            }


            /*
             * Save user information
             */

            localStorage.setItem(
                "user",
                JSON.stringify(user)
            );


            /*
             * Verify selected role
             *
             * The backend role is authoritative.
             */

            if (user.role !== selectedRole) {

                localStorage.removeItem("access_token");
                localStorage.removeItem("user");

                throw new Error(
                    `This account is registered as ${user.role}.`
                );

            }


            /*
             * Redirect based on role
             */

            if (user.role === "CITIZEN") {

                window.location.href = "citizen.html";

            } else if (user.role === "AUTHORITY") {

                window.location.href = "authority.html";

            }

        } catch (error) {

            errorMessage.textContent =
                error.message;

        }

    });