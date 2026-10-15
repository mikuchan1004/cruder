document.querySelectorAll('.icon-bookmark').forEach((star) => {

    star.addEventListener('click', async () => {
        const jobId = star.dataset.jobId
        
        try {
            const response = await fetch(
                `/jobgogo/bookmark/${jobId}`,
                {
                    method: 'POST'
                }
            )

            const data = await response.json()

            if (response.status === 401) {
                alert('로그인이 필요합니다.')
                return
            }

            if (!response.ok || !data.success) {
                console.error(
                    '북마크 처리 실패:',
                    data
                )

                alert(
                    data.message ?? '북마크 처리에 실패했습니다.'
                )

                return
            }

            if (data.bookmarked) {
                star.classList.remove('fa-regular')
                star.classList.add('fa-solid')
            } else {
                star.classList.remove('fa-solid')
                star.classList.add('fa-regular')
            }
        } catch (error) {
            console.error(
                '북마크 요청 오류:',
                error
            )

            alert('북마크 요청 중 오류가 발생했습니다.')
        }
    })
})