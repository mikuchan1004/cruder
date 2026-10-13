const params = new URLSearchParams(window.location.search)

if (params.get('login') === 'success') {
    alert('로그인되었습니다.')

    // alert를 한 번 띄운 뒤 URL에서 ?login=success 제거
    window.history.replaceState(
        {},
        document.title,
        window.location.pathname
    )
}