import { Routes, Route } from "react-router-dom";
import { Welcome } from "./pages/Welcome";
import { Journey } from "./pages/Journey";
import { Summary } from "./pages/Summary";

// Deliberately no "run everything" route and no dashboard-style landing --
// the app enters at Welcome, only reaches Summary at the end (or if the
// user explicitly asks for the overview). See ../README.md.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/journey/:stepId" element={<Journey />} />
      <Route path="/summary" element={<Summary />} />
    </Routes>
  );
}
