// Sample dataset
const students = [
  { id: 1, name: "Solomon Nwante", grades: [85, 90, 78] },
  { id: 2, name: "Odesomi Adeleke", grades: [95, 88, 92] },
  { id: 3, name: "Latunde Oluwanifemi", grades: [70, 75, 80] },
  { id: 4, name: "Jummie Jummie", grades: [88, 85, 91] },
];

// Function to calculate average grades
function calculateAverageGrades(data) {
  return data.map((student) => {
    const total = student.grades.reduce((sum, grade) => sum + grade, 0);
    const avg = total / student.grades.length;
    return {
      id: student.id,
      name: student.name,
      averageGrade: Number(avg.toFixed(2)),
    };
  });
}

// Function to find the top student
function findTopStudent(data) {
  const averages = calculateAverageGrades(data);
  return averages.reduce((top, student) =>
    student.averageGrade > top.averageGrade ? student : top
  );
}

// Function to sort students by average grade
function sortStudentsByGrade(data) {
  const averages = calculateAverageGrades(data);
  return averages.sort((a, b) => b.averageGrade - a.averageGrade);
}

// Output examples
console.log("Average Grades:");
console.log(calculateAverageGrades(students));

console.log("\nTop Student:");
console.log(findTopStudent(students));

console.log("\nSorted Students:");
console.log(sortStudentsByGrade(students));
