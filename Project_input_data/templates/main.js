function formData(){
    // Prevent the default form submission
    event.preventDefault();
    //Access the form first
    let myForm= document.getElementById("myform");
    //Accessing the form element's values now
    let name = myForm.elements["username"].value;
    let Address1= myForm.elements["address1"].value;
    let Address2= myForm.elements["address2"].value;
    let City= myForm.elements["city"].value;
    let Country= myForm.elements["country"].value;
    let ZipCode= myForm.elements["zipcode"].value;

    //Select the table or accessing the table
    let myTable= document.getElementById("datatable");
    //Now, insert rows for every data entry at the end of the table
    let newRow= myTable.insertRow(-1);
    //Add corresponding data to each cell  in the row
    let Cell1= newRow.insertCell(0);
    let Cell2= newRow.insertCell(1);
    let Cell3= newRow.insertCell(2);
    let Cell4= newRow.insertCell(3);
    let Cell5= newRow.insertCell(4);
    let Cell6= newRow.insertCell(5);
//filling each cell with corresponding values obtained from the form elements using name tag
   Cell1.innerHTML= name;
   Cell2.innerHTML= Address1;
   Cell3.innerHTML= Address2;
   Cell4.innerHTML= City;
   Cell5.innerHTML= Country;
   Cell6.innerHTML= ZipCode;

}
//LEARNINGS:
//prompt()--- asks the user for input similar to  the alert message box but asks for the input
//preventDefault()
//insertRow()
//insertCell()
//object.innerHTML= value
//object.elemets["name"].value
