const params = new URLSearchParams(window.location.search)

if (params.get('edit') === 'success') {
    alert('회원 정보가 수정되었습니다.')

    // alert를 한 번 띄운 뒤 URL에서 ?edit=success 제거
    window.history.replaceState(
        {},
        document.title,
        window.location.pathname
    )
}