<?php
session_start();
require __DIR__ . '/connect.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  header('Location: login.html');
  exit;
}

$name  = trim($_POST['name']  ?? '');
$email = strtolower(trim($_POST['email'] ?? ''));
$phone = trim($_POST['phone'] ?? '');

if ($name === '' || $email === '' || $phone === '') {
  exit('All fields are required.');
}

$stmt = $pdo->prepare('SELECT id FROM users_basic WHERE email = ? OR phone = ? LIMIT 1');
$stmt->execute([$email, $phone]);
$existing = $stmt->fetch();

if ($existing) {
  $upd = $pdo->prepare('UPDATE users_basic SET name = ?, email = ?, phone = ? WHERE id = ?');
  $upd->execute([$name, $email, $phone, $existing['id']]);
  $userId = (int)$existing['id'];
} else {
  $ins = $pdo->prepare('INSERT INTO users_basic (name, email, phone) VALUES (?, ?, ?)');
  $ins->execute([$name, $email, $phone]);
  $userId = (int)$pdo->lastInsertId();
}

session_regenerate_id(true);
$_SESSION['user_id'] = $userId;
$_SESSION['name'] = $name;
$_SESSION['email'] = $email;

header('Location: dashboard.php');
exit;