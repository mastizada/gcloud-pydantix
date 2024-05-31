test:
    ifdef target
			pytest --cov=gcloud --cov-report html $(target) -vvvv -W ignore::DeprecationWarning -W error::RuntimeWarning
    else
			pytest --cov=gcloud --cov-report html "tests" -vvvv -W ignore::DeprecationWarning -W error::RuntimeWarning
    endif
