<?php
session_start();
if (!isset($_SESSION['user_id'])) {
  header('Location: login.html');
  exit;
}
?>
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Dashboard</title></head>
<body>
  <h1>Welcome, <?php echo htmlspecialchars($_SESSION['name']); ?></h1>
  <p>Email: <?php echo htmlspecialchars($_SESSION['email']); ?></p>
  <a href="logout.php">Logout</a>
</body>
</html>