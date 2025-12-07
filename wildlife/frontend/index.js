if (document.readyState === "loading") {
 
  document.addEventListener("DOMContentLoaded", main);
} else {

  main();
}



function main() {


    

    const searchbar = document.getElementById("search");

    searchbar.addEventListener("search", (event) => {

      


        const query = searchbar.value;
        //console.log("Search query:", query);
        const spawner = require("child_process").spawn;
        const python_process = spawner("python", ["./search_cli.py", query]);
        
        python_process.stdout.on("data", (data) => {
            const results = data.toString().split("\n").filter(line => line.trim() !== "");
        });



    });



    const resultsContainer = document.getElementById("results");






  
}
